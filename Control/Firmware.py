#Firmware layer for calls from the drone interface 


# Firmware layer — MAVLink / ArduPilot implementation
# Last updated: Richard Nguyen April 25, 2026

from pymavlink import mavutil
import time


class FlightFirmware:
    """
        serial : FlightFirmware("serial:///dev/ttyAMA0:57600")
        UDP    : FlightFirmware("udp:127.0.0.1:14550")   ← SITL default
        TCP    : FlightFirmware("tcp:127.0.0.1:5760")
    """

    def __init__(self, connection_string: str = "udp:127.0.0.1:14550"):
        print(f"Connecting to ArduPilot: {connection_string}")
        self.mav = mavutil.mavlink_connection(connection_string)
        self.mav.wait_heartbeat()
        print(
            f"Heartbeat received  (system {self.mav.target_system}, "
            f"component {self.mav.target_component})"
        )

    #helpers 
    def _send_command_long(self, command, param1=0, param2=0, param3=0,
                           param4=0, param5=0, param6=0, param7=0,
                           wait_ack=True):
        self.mav.mav.command_long_send(
            self.mav.target_system,
            self.mav.target_component,
            command,
            0,          # confirmation
            param1, param2, param3, param4, param5, param6, param7,
        )
        if wait_ack:
            ack = self.mav.recv_match(type="COMMAND_ACK", blocking=True, timeout=5)
            if ack and ack.result != mavutil.mavlink.MAV_RESULT_ACCEPTED:
                print(f"Command {command} not accepted — MAV_RESULT={ack.result}")

    def _set_mode(self, mode_name: str):
        mode_id = self.mav.mode_mapping().get(mode_name)
        if mode_id is None:
            raise ValueError(f"Unknown flight mode: {mode_name}")
        self.mav.mav.set_mode_send(
            self.mav.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
        )

    #arm and disarm methods
    def arm(self):
        self._set_mode("GUIDED")
        self._send_command_long(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=1,   # 1 = arm
        )
        print("MAVLink: armed")

    def disarm(self):
        self._send_command_long(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=0,   # 0 = disarm
        )
        print("MAVLink: disarmed")

    #takeoff and landing methods
    def takeoff(self, altitude_m: float = 5.0):
        self._send_command_long(
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            param7=altitude_m,
        )
        print(f"MAVLink: takeoff commanded to {altitude_m} m")

        #wait until we reach the target altitude
        while True:
            msg = self.mav.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=10)
            if msg is None:
                print("Warning: no GLOBAL_POSITION_INT received during takeoff wait")
                break
            current_alt = msg.relative_alt / 1000.0   # mm → m
            if current_alt >= altitude_m * 0.90:
                print(f"MAVLink: reached altitude {current_alt:.1f} m")
                break

    def land(self):
        self._set_mode("LAND")
        print("MAVLink: LAND mode set")

    def emergency_land(self):
        self._send_command_long(
            mavutil.mavlink.MAV_CMD_DO_FLIGHTTERMINATION,
            param1=1,
        )
        print("MAVLink: FLIGHT TERMINATION sent (emergency)")

