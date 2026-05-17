import time

import Vision
import Control
import waypoint

from pymavlink import mavutil

from Mission.handoff import Handoff

SPEED = 0.5


class EndExecution(Exception):
    """A simple breaking exception to raise when the label is None (for now),
    better implementation soon"""

    def __init__(self, exit_code: int, message: str = ""):
        self._exit_code = exit_code
        self._message = message


    def __str__(self):
        if self._exit_code == 0:
            return f"Healthy Termination {("Additional Information: " + self._message) if self._message else ""})"
        else:
            return (f"Erroneous Termination: Additional Information: "
                    f"Exit Code: {self._exit_code}, "
                    f"Message: {self._message}")

class DroneNavigator:
    """Class to bundle Drone's location info + connection info"""

    def __init__(self, conn: str, file_path: str = ""):
        self._waypoints_data = waypoint.Waypoint.generate_from(input()) if file_path == "" else waypoint.Waypoint.generate_from(file_path)

        conn = ""
        print(f"Connecting to {conn}")

        self._master = mavutil.mavlink_connection(conn)

        # Check heartbeat
        self._master.wait_heartbeat()
        print(
            f"Successfully connected to {conn}! Target System: {self._master.target_system} Target Component: {self.master.target_component}")

        self._current_lat: float = 0.0
        self._current_lon: float = 0.0
        self._current_alt: float = 0.0
        self._gps_fixed: bool = False


    def main(self) -> None:
        """Main Loop of the DroneNavigator"""
        try:
            self._consume_waypoints(self._master)
        except EndExecution as e:
            print(e)


    def _update_localization(self):
        """Updates the localization info by polling mavlink"""
        # Non-blocking check for new messages

        msg = self._master.recv_match(type=['GLOBAL_POSITION_INT', 'GPS_RAW_INT'], blocking=False)

        if msg is None:
            return

        if msg.get_type() == 'GLOBAL_POSITION_INT':
            # Extracting GPS coordinates from the EKF (Extended Kalman Filter) output
            # These values are scaled by 1e7 in mavlink
            self.current_lat = msg.lat / 1e7
            self.current_lon = msg.lon / 1e7
            self.current_alt = msg.alt / 1000.0  # Convert mm to meters
            self.gps_fixed = True
            print(f"Localized: Lat: {self.current_lat:.6f}, Lon: {self.current_lon:.6f}, Alt: {self.current_alt:.2f}m")

        elif msg.get_type() == 'GPS_RAW_INT':
            # Check if GPS fix is achieved (fix_type > 0)
            if msg.fix_type >= 3:  # 3 = 3D Fix
                self.gps_fixed = True


    def _consume_waypoints(self, connection) -> None:
        """Consume the waypoints and send to the drone one by one"""

        print(f"Starting a mission... Loaded {len(self._waypoints_data)} waypoints.")

        time.sleep(5) # Wait a bit before starting, for GPS lock

        if not self._gps_fixed:
            print("Cannot start mission yet; GPS not locked")
            raise ValueError()

        for wp in self._waypoints_data:
            self._update_localization()
            print(f"Executing waypoint with ID {wp.waypoint_id}")

            if self._gps_fixed:
                self._consume_waypoint(connection, wp)

        raise EndExecution(1)


    def _consume_waypoint(self, connection, wp: waypoint.Waypoint) -> bool:
        """Helper to separate code"""
        if wp.marker_type == waypoint.MarkerType.HANDOFF_VISION:
            self._handoff(Vision)
        elif wp.marker_type == waypoint.MarkerType.HANDOFF_CONTROL:
            self._handoff(Control)
        else:
            lat_to_send = int(wp.lat * 1e7)
            lon_to_send = int(wp.lon * 1e7) # Conversion for the two
            alt_to_send = int(wp.alt * 1000)

            self._master.set_position_target_global_int_send(
                int(time.time()),
                self._master.target_system,
                self._master.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                0b0000111111111000,                             # Bit mask to ignore the speed, velocity, and acceleration
                lat_to_send, lon_to_send, alt_to_send,
                0, 0, 0,                                        # Velocity
                0, 0, 0,                                        # Acceleration
                0, 0                                            # Yaw
        )

        return True


    def _handoff(self, handoff_to: Handoff):
        handoff_to.execute_handoff(self, self._master)


if __name__ == "__main__":
    """This method grabs the frame every single tick and represents the main
    execution pipeline; Handles the actual connection aspect"""

    connection_url = "udp:127.0.0.1:14550"

    drone = DroneNavigator(connection_url)

    drone.main()