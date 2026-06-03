"""MAVLink drone abstraction.

`Drone` owns the MAVLink connection (the "master") and exposes telemetry and
movement primitives that higher-level modules build on. Mission and Control
share a single `Drone` instance rather than touching pymavlink directly.

This module speaks pure MAVLink and holds no mission policy: acceptance radii
and timeouts are passed in by the caller, not baked in here.
"""

import math
import time

from pymavlink import mavutil

METERS_PER_DEG = math.pi / 180.0 * 6_371_000.0  # Earth radius in meters

# MAV_CMD_DO_ORBIT (34) is absent from the bundled pymavlink dialect, but
# command_long carries the command as a raw int, so we send it by id. The
# autopilot (ArduPilot 4.x / PX4) decodes it as long as its firmware supports it.
MAV_CMD_DO_ORBIT = 34


def horizontal_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Horizontal distance between two lat/lon points in meters"""

    d_lat = (lat2 - lat1) * METERS_PER_DEG
    d_lon = (lon2 - lon1) * METERS_PER_DEG * math.cos(math.radians((lat1 + lat2) / 2))

    return math.hypot(d_lat, d_lon)


class Drone:
    """Thin abstraction over a MAVLink connection for Mission and Control."""

    # Position-target mask: ignore velocity, acceleration, yaw, yaw rate.
    _POS_TARGET_IGNORE_MASK = 0b0000111111111000

    # Velocity-target mask: use vx/vy/vz and yaw rate, ignore everything else.
    _VEL_TARGET_IGNORE_MASK = 0b0000011111000111

    def __init__(self, conn: str):
        print(f"Connecting to {conn}")
        self._master = mavutil.mavlink_connection(conn)

        self._master.wait_heartbeat()
        print(
            f"Successfully connected to {conn}! "
            f"Target System: {self._master.target_system} "
            f"Target Component: {self._master.target_component}"
        )

        self._lat: float = 0.0
        self._lon: float = 0.0
        self._alt: float = 0.0  # AMSL
        self._relative_alt: float = 0.0  # above home/launch
        self._gps_fixed: bool = False
        # True only once a real position (GLOBAL_POSITION_INT) has been received.
        # GPS_RAW_INT alone sets _gps_fixed but leaves lat/lon/alt at 0,0,0.
        self._has_position: bool = False

    @property
    def master(self):
        """The underlying pymavlink connection, for advanced/uncovered cases."""

        return self._master

    @property
    def position(self) -> tuple[float, float, float]:
        """Last known (lat, lon, alt) in degrees / meters."""

        return self._lat, self._lon, self._alt

    @property
    def gps_fixed(self) -> bool:
        return self._gps_fixed

    # Telemetry

    def update_localization(self) -> None:
        """Poll mavlink once (non-blocking) and refresh cached position."""
        msg = self._master.recv_match(
            type=["GLOBAL_POSITION_INT", "GPS_RAW_INT"], blocking=False
        )

        if msg is None:
            return

        if msg.get_type() == "GLOBAL_POSITION_INT":
            # GPS coordinates from the EKF output, scaled by 1e7 in mavlink.
            self._lat = msg.lat / 1e7
            self._lon = msg.lon / 1e7
            self._alt = msg.alt / 1000.0  # AMSL, mm -> m
            self._relative_alt = msg.relative_alt / 1000.0  # above home, mm -> m
            self._gps_fixed = True
            self._has_position = True
            print(
                f"Localized: Lat: {self._lat:.6f}, "
                f"Lon: {self._lon:.6f}, Alt: {self._alt:.2f}m"
            )

        elif msg.get_type() == "GPS_RAW_INT":
            if msg.fix_type >= 3:  # 3 = 3D Fix
                self._gps_fixed = True

    def wait_for_gps_lock(self, timeout: float) -> bool:
        """Block until a usable position fix is available. False on timeout.

        Waits for an actual GLOBAL_POSITION_INT (not merely a GPS_RAW_INT fix),
        so callers can trust `position` afterward.
        """

        deadline = time.time() + timeout
        while time.time() < deadline:
            self.update_localization()
            if self._has_position:
                return True
            time.sleep(0.1)
        return False

    def wait_for_altitude(
        self, target_alt: float, tolerance: float, timeout: float
    ) -> bool:
        """Block until within `tolerance` m of `target_alt` (relative to home).

        Used after takeoff so the climb completes before the next leg. Returns
        False on timeout.
        """

        deadline = time.time() + timeout
        while time.time() < deadline:
            self.update_localization()
            if self._relative_alt >= target_alt - tolerance:
                return True
            time.sleep(0.2)
        return False

    def distance_to(self, lat: float, lon: float) -> float:
        """Horizontal distance (meters) from last known position to a point."""

        return horizontal_distance_m(self._lat, self._lon, lat, lon)

    def wait_for_arrival(
        self, lat: float, lon: float, radius: float, timeout: float
    ) -> bool:
        """Block until within `radius` meters of the target. False on timeout."""

        deadline = time.time() + timeout
        while time.time() < deadline:
            self.update_localization()
            if self.distance_to(lat, lon) <= radius:
                return True
            time.sleep(0.2)
        return False

    # Mavlink Commands

    def set_mode(self, mode: str) -> None:
        """Set the flight mode by name (e.g. 'GUIDED', 'LAND')."""

        mode_id = self._master.mode_mapping().get(mode)
        if mode_id is None:
            raise ValueError(f"Unknown flight mode: {mode}")
        self._master.set_mode(mode_id)

    def arm(self) -> None:
        """Arm the motors."""

        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # confirmation
            1,  # param1: 1 = arm
            0,
            0,
            0,
            0,
            0,
            0,
        )

    def disarm(self) -> None:
        """Disarm the motors."""

        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # confirmation
            0,  # param1: 0 = disarm
            0,
            0,
            0,
            0,
            0,
            0,
        )

    def goto(self, lat: float, lon: float, alt: float) -> None:
        """Command the drone toward a global position (relative altitude)."""

        self._master.mav.set_position_target_global_int_send(
            0,  # time_boot_ms (0 = ignore)
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            self._POS_TARGET_IGNORE_MASK,
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
            0,
            0,
            0,  # Velocity
            0,
            0,
            0,  # Acceleration
            0,
            0,  # Yaw, yaw rate
        )

    def send_velocity(
        self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0
    ) -> None:
        """Command a body-frame velocity (m/s) and yaw rate (rad/s).

        Useful for Control's incremental movement primitives.
        """

        self._master.mav.set_position_target_local_ned_send(
            0,  # time_boot_ms (0 = ignore)
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            self._VEL_TARGET_IGNORE_MASK,
            0,
            0,
            0,  # Position
            vx,
            vy,
            vz,  # Velocity
            0,
            0,
            0,  # Acceleration
            0,
            yaw_rate,  # Yaw, yaw rate
        )

    @staticmethod
    def _scaled_velocity(
        direction: tuple[float, float, float], speed: float
    ) -> tuple[float, float, float]:
        """Normalize `direction` and scale to `speed`, validating both."""
        if speed <= 0:
            raise ValueError("`speed` must be positive")
        norm = math.sqrt(sum(c * c for c in direction))
        if norm == 0:
            raise ValueError("`direction` must be a non-zero vector")
        return tuple(c / norm * speed for c in direction)

    def _displacement_from(
        self, start_lat: float, start_lon: float, start_alt: float
    ) -> float:
        """3D distance (meters) of the current position from a start point."""
        horizontal = self.distance_to(start_lat, start_lon)
        vertical = self._alt - start_alt
        return math.sqrt(horizontal * horizontal + vertical * vertical)

    def move_for_duration(
        self,
        direction: tuple[float, float, float],
        speed: float,
        duration: float,
        rate_hz: float = 10.0,
    ) -> None:
        """Travel along a body-frame direction at `speed` m/s for `duration` s.

        `direction` is a (forward, right, down) vector; it is normalized here,
        so it need not be exactly unit length. The velocity setpoint is re-sent
        at `rate_hz` for the whole window (MAVLink velocity targets expire
        quickly), then a zero-velocity stop is issued.
        """

        if duration < 0:
            raise ValueError("`duration` must be non-negative")

        vx, vy, vz = self._scaled_velocity(direction, speed)

        deadline = time.time() + duration
        interval = 1.0 / rate_hz
        while time.time() < deadline:
            self.send_velocity(vx, vy, vz)
            time.sleep(interval)

        self.send_velocity(0.0, 0.0, 0.0)  # stop and hold

    def move_for_distance(
        self,
        direction: tuple[float, float, float],
        speed: float,
        distance: float,
        rate_hz: float = 10.0,
        timeout: float | None = None,
    ) -> bool:
        """Travel along a body-frame direction for `distance` meters.

        Closed-loop: streams the velocity setpoint at `rate_hz` while measuring
        actual GPS displacement from the start fix, and stops once that
        displacement reaches `distance`. `direction` is a (forward, right, down)
        vector, normalized here (see `move_for_duration` for semantics).

        `timeout` bounds the move so a blocked/stalled drone can't stream
        forever; it defaults to twice the ideal time (`distance / speed`) plus
        a 5 s margin. Returns True if the distance was reached, False on timeout.
        """

        if distance < 0:
            raise ValueError("`distance` must be non-negative")

        vx, vy, vz = self._scaled_velocity(direction, speed)

        if timeout is None:
            timeout = (distance / speed) * 2.0 + 5.0

        deadline = time.time() + timeout

        # Capture the start fix only once a real position is available; acting on
        # the (0, 0, 0) sentinel would make displacement jump and stop instantly.
        while not self._has_position and time.time() < deadline:
            self.update_localization()
            time.sleep(0.05)
        if not self._has_position:
            print("move_for_distance: no position fix; aborting")
            return False
        start_lat, start_lon, start_alt = self.position

        interval = 1.0 / rate_hz
        reached = False
        while time.time() < deadline:
            self.send_velocity(vx, vy, vz)
            self.update_localization()
            if self._displacement_from(start_lat, start_lon, start_alt) >= distance:
                reached = True
                break
            time.sleep(interval)

        self.send_velocity(0.0, 0.0, 0.0)  # stop and hold
        if not reached:
            print(f"move_for_distance timed out before reaching {distance:.1f}m")
        return reached

    def takeoff(self, altitude: float) -> None:
        """Command a takeoff to the given relative altitude (meters)."""

        print(f"Taking off to {altitude:.1f}m")
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,  # confirmation
            0,
            0,
            0,
            0,  # params 1-4 (unused)
            0,
            0,  # lat, lon (0 = current)
            altitude,  # param7: target altitude
        )

    def land(self) -> None:
        """Command a landing at the current position."""

        print("Landing")
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,  # confirmation
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )

    def hold_position(
        self,
        lat: float | None = None,
        lon: float | None = None,
        alt: float | None = None,
    ) -> None:
        """Actively hold (loiter) at the given or current position.

        In GUIDED this re-asserts a position setpoint so the vehicle holds even
        if a velocity setpoint had previously been streamed. The caller decides
        how long to wait; this just commands the hold.
        """
        if lat is None or lon is None or alt is None:
            lat, lon, alt = self._lat, self._lon, self._alt
        print(f"Holding at {lat:.6f}, {lon:.6f}, {alt:.2f}m")
        self.goto(lat, lon, alt)

    def return_to_launch(self) -> None:
        """Return to the launch point and land (RTL)."""
        print("Returning to launch")
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            0,  # confirmation
            0, 0, 0, 0, 0, 0, 0,
        )

    def change_speed(self, speed: float, airspeed: bool = False) -> None:
        """Set the cruise speed (m/s) used by subsequent position legs.

        `airspeed=False` sets ground speed (the usual choice for multirotors).
        """
        print(f"Changing speed to {speed:.1f} m/s")
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED,
            0,                       # confirmation
            0 if airspeed else 1,    # param1: speed type (0=air, 1=ground)
            speed,                   # param2: speed (m/s)
            -1,                      # param3: throttle (-1 = no change)
            0, 0, 0, 0,              # param4-7 (unused)
        )

    def orbit(
        self,
        radius: float,
        speed: float,
        turns: float,
        lat: float | None = None,
        lon: float | None = None,
        alt: float | None = None,
    ) -> None:
        """Circle a center point `turns` times at `radius` m and `speed` m/s.

        Uses MAV_CMD_DO_ORBIT (ArduPilot 4.x / PX4). Center defaults to the
        current position. A positive `radius` orbits clockwise, negative
        counter-clockwise. Note: COMMAND_LONG carries the center lat/lon as
        float32 (~1 m resolution), so this is for debug/loose orbits, not
        survey-grade centering.
        """
        if lat is None or lon is None or alt is None:
            lat, lon, alt = self._lat, self._lon, self._alt
        print(f"Orbiting r={radius:.1f}m x{turns} at {speed:.1f} m/s")
        self._master.mav.command_long_send(
            self._master.target_system,
            self._master.target_component,
            MAV_CMD_DO_ORBIT,
            0,          # confirmation
            radius,     # param1: radius (m), sign = direction
            speed,      # param2: tangential velocity (m/s)
            0,          # param3: yaw behavior (0 = face center)
            turns,      # param4: number of orbits
            lat,        # param5: center latitude
            lon,        # param6: center longitude
            alt,        # param7: center altitude
        )
