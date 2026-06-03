import math
import time

from typing import Optional, Protocol, runtime_checkable

import waypoint

from drone import Drone


# Acceptance radius (meters) for considering a waypoint "reached".
ACCEPTANCE_RADIUS_M = 1.5
# How long to wait for the drone to reach a waypoint before giving up.
ARRIVAL_TIMEOUT_S = 120.0
# How long to wait for an initial GPS lock before aborting the mission.
GPS_LOCK_TIMEOUT_S = 30.0
# Tangential speed (m/s) for LOITER_TURNS orbits (not stored in the waypoint).
ORBIT_SPEED_MS = 2.0
# Altitude band (meters) for considering a takeoff climb complete.
ALTITUDE_TOLERANCE_M = 0.5
# How long to wait for the takeoff climb before giving up.
TAKEOFF_TIMEOUT_S = 60.0
# Max number of fine-movement corrections before giving up on visual anchoring.
ANCHOR_MAX_ITERATIONS = 10


# --- Visual-anchoring hook contracts -------------------------------------
#
# Mission orchestrates the anchor loop but does NOT implement detection or the
# movement calculation. The Camera/Vision/Control collaborators are injected
# into DroneNavigator; these Protocols document the interface Mission expects,
# so Vision and Control can be developed independently against this contract.


@runtime_checkable
class Camera(Protocol):
    def get_frame(self) -> object | None:
        """Return the latest camera frame, or None if unavailable."""
        ...


@runtime_checkable
class VisionDetector(Protocol):
    def run_detection(self, frame: object | None) -> Optional[dict]:
        """Detect a physical waypoint in `frame`.

        Returns a dict with at least ``{"detected": bool}``; when detected, it
        also carries the waypoint's image-space offset for Control to act on.
        """
        ...


@runtime_checkable
class AnchorController(Protocol):
    def anchor_command(
        self, detection: dict
    ) -> Optional[tuple[tuple[float, float, float], float, float]]:
        """Compute the fine move that anchors the drone onto the detection.

        Returns ``(direction, speed_m_s, duration_s)`` where ``direction`` is a
        body-frame (forward, right, down) vector, or ``None`` once the drone is
        considered anchored/centered (no further correction needed).
        """
        ...


class EndExecution(Exception):
    """A simple breaking exception to raise when the label is None (for now),
    better implementation soon"""

    def __init__(self, exit_code: int, message: str = ""):
        self._exit_code = exit_code
        self._message = message

    def __str__(self):
        if self._exit_code == 0:
            return f"Healthy Termination {('Additional Information: ' + self._message) if self._message else ''})"
        else:
            return (
                f"Erroneous Termination: Additional Information: "
                f"Exit Code: {self._exit_code}, "
                f"Message: {self._message}"
            )


class DroneNavigator:
    """Drives a mission over a shared `Drone`.

    Mission owns the `Drone` (and therefore the MAVLink link) and passes it
    into the other modules (Vision, Control) as needed -- there is no
    ownership handoff. This class holds mission policy only; all MAVLink and
    telemetry lives on `Drone`.

    Optional `camera`, `vision`, and `control` collaborators enable visual
    anchoring: after GPS-arriving at a waypoint, Mission asks Vision to detect
    the physical marker and Control to compute a fine move, then executes it on
    the `Drone`. When any of them is absent, GPS arrival is final.
    """

    def __init__(
        self,
        drone: Drone,
        waypoints: list[waypoint.Waypoint],
        *,
        camera: Optional[Camera] = None,
        vision: Optional[VisionDetector] = None,
        control: Optional[AnchorController] = None,
    ):
        self._drone = drone
        self._waypoints_data = waypoints
        self._camera = camera
        self._vision = vision
        self._control = control

    def main(self) -> None:
        """Main Loop of the DroneNavigator"""
        try:
            self._consume_waypoints()
        except EndExecution as e:
            print(e)

    def _consume_waypoints(self) -> None:
        """Consume the waypoints and send to the drone one by one."""

        print(f"Starting a mission... Loaded {len(self._waypoints_data)} waypoints.")

        if not self._drone.wait_for_gps_lock(GPS_LOCK_TIMEOUT_S):
            raise EndExecution(1, "GPS lock not acquired within timeout")

        for wp in self._waypoints_data:
            print(
                f"Executing waypoint with ID {wp.waypoint_id} ({wp.marker_type.name})"
            )
            self._consume_waypoint(wp)

        raise EndExecution(0, "All waypoints completed")

    def _consume_waypoint(self, wp: waypoint.Waypoint) -> None:
        """Dispatch a single waypoint to the appropriate handler."""
        mt = waypoint.MarkerType
        t = wp.marker_type

        # Behaviors that don't fly to the waypoint position.
        if t == mt.TAKEOFF:
            self._drone.takeoff(wp.alt)
            climbed = self._drone.wait_for_altitude(
                wp.alt, ALTITUDE_TOLERANCE_M, TAKEOFF_TIMEOUT_S
            )
            if not climbed:
                raise EndExecution(1, "Timed out reaching takeoff altitude")
            print(f"Reached takeoff altitude {wp.alt:.1f}m")
            return
        if t == mt.LAND:
            self._drone.land()
            return
        if t == mt.RETURN_TO_LAUNCH:
            self._drone.return_to_launch()
            return
        if t == mt.CHANGE_SPEED:
            self._drone.change_speed(wp.params[1])  # PARAM2 = speed (m/s)
            return

        # Everything below first flies to the waypoint coordinates.
        self._fly_to(wp)

        if t == mt.LOITER_TURNS:
            radius = wp.params[2]   # PARAM3 = loiter radius
            turns = wp.params[0]    # PARAM1 = number of turns
            self._drone.orbit(
                radius=radius,
                speed=ORBIT_SPEED_MS,
                turns=turns,
                lat=wp.lat,
                lon=wp.lon,
                alt=wp.alt,
            )
            # orbit() is fire-and-forget; block while the autopilot flies the
            # turns so the next leg doesn't override the orbit immediately.
            orbit_seconds = 2 * math.pi * abs(radius) * turns / ORBIT_SPEED_MS
            print(f"Orbiting for {orbit_seconds:.1f}s")
            time.sleep(orbit_seconds)
        elif t == mt.LOITER_TIME:
            self._loiter(wp, seconds=wp.params[0])  # PARAM1 = loiter time
        elif t == mt.LOITER_UNLIM:
            self._loiter(wp, seconds=None)
        else:  # WAYPOINT
            self._anchor_to_waypoint(wp)
            if wp.hold_time > 0:
                print(f"Holding for {wp.hold_time:.1f}s")
                time.sleep(wp.hold_time)

    def _anchor_to_waypoint(self, wp: waypoint.Waypoint) -> None:
        """Fine-anchor onto a vision-detected physical waypoint.

        HOOK / integration seam. Mission only orchestrates the loop:
          1. grab a frame from the Camera,
          2. ask Vision to detect the physical waypoint,
          3. ask Control for the fine move (direction + speed + duration),
          4. execute it on the Drone,
        repeating until Control reports the drone is anchored (returns None) or
        a correction budget is exhausted. Detection and the movement math live
        in Vision and Control; this method implements neither.

        No-op unless both a vision detector and an anchor controller are
        injected (GPS arrival is then final).
        """
        if self._vision is None or self._control is None:
            return

        for attempt in range(ANCHOR_MAX_ITERATIONS):
            frame = self._camera.get_frame() if self._camera is not None else None
            detection = self._vision.run_detection(frame)  # HOOK: Vision

            if not detection or not detection.get("detected"):
                if attempt == 0:
                    print("No physical waypoint detected; skipping anchor")
                return

            command = self._control.anchor_command(detection)  # HOOK: Control
            if command is None:
                print(f"Anchored onto waypoint {wp.waypoint_id}")
                return

            direction, speed, duration = command
            self._drone.move_for_duration(direction, speed, duration)

        print(
            f"Anchor: gave up on waypoint {wp.waypoint_id} after "
            f"{ANCHOR_MAX_ITERATIONS} corrections"
        )

    def _fly_to(self, wp: waypoint.Waypoint) -> None:
        """Send the drone to a waypoint's coordinates and block until arrival."""
        self._drone.goto(wp.lat, wp.lon, wp.alt)
        arrived = self._drone.wait_for_arrival(
            wp.lat, wp.lon, ACCEPTANCE_RADIUS_M, ARRIVAL_TIMEOUT_S
        )
        if not arrived:
            raise EndExecution(1, f"Timed out reaching waypoint {wp.waypoint_id}")
        print(f"Reached waypoint {wp.waypoint_id}")

    def _loiter(self, wp: waypoint.Waypoint, seconds: float | None) -> None:
        """Hold at a waypoint for `seconds`, or indefinitely if None."""
        self._drone.hold_position(wp.lat, wp.lon, wp.alt)
        if seconds is None:
            print("Loitering indefinitely (Ctrl-C to abort)")
            while True:
                time.sleep(1.0)
        print(f"Loitering for {seconds:.1f}s")
        time.sleep(seconds)


if __name__ == "__main__":
    """This method grabs the frame every single tick and represents the main
    execution pipeline; Handles the actual connection aspect"""

    connection_url = "udp:127.0.0.1:14550"

    drone = Drone(connection_url)
    waypoints = waypoint.Waypoint.generate_from(input())

    # Visual anchoring is opt-in: inject the collaborators to enable it, e.g.
    #   import Vision, Control
    #   navigator = DroneNavigator(
    #       drone, waypoints,
    #       camera=Vision.Camera(), vision=Vision, control=Control.Anchorer(drone),
    #   )
    # Left unset here so Mission runs standalone (GPS arrival is final).
    DroneNavigator(drone, waypoints).main()
