# Drone Control Module — Top layer
# Last updated: Richard Nguyen April 25, 2026

from firmware import FlightFirmware


class DroneController:
    """
    High-level drone interface.  Talks only to FlightFirmware; never
    touches MAVLink directly.  All MAVLink details live in firmware.py.
    """

    def __init__(self, connection_string: str = "udp:127.0.0.1:14550"):
        self.firmware = FlightFirmware(connection_string)
        self.armed    = False
        self.airborne = False

    #states and arming methods
    def arm(self):
        self.firmware.arm()
        self.armed = True
        print("Armed")

    def disarm(self):
        if self.airborne:
            print("Cannot disarm while airborne.")
            return
        self.firmware.disarm()
        self.armed = False
        print("Disarmed")

    def takeoff(self, altitude_m: float = 5.0):
        if not self.armed:
            self.arm()
        self.firmware.takeoff(altitude_m)
        self.airborne = True
        print("Takeoff!")

    def land(self):
        if not self.armed:
            print("Drone is not armed.")
            return
        self.firmware.land()
        self.airborne = False
        print("Landing!")

    def emergency_land(self):
        self.firmware.emergency_land()
        self.airborne = False
        print("Emergency landing triggered.")

    #movement methods
    def move_forward(self, speed: float = 0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=speed, roll=0.0, yaw=0.0)

    def move_backward(self, speed: float = 0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=-speed, roll=0.0, yaw=0.0)

    def move_left(self, speed: float = 0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=-speed, yaw=0.0)

    def move_right(self, speed: float = 0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=speed, yaw=0.0)

    def ascend(self, speed: float = 0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5 + speed, pitch=0.0, roll=0.0, yaw=0.0)

    def descend(self, speed: float = 0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5 - speed, pitch=0.0, roll=0.0, yaw=0.0)

    def rotate_left(self, speed: float = 0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=0.0, yaw=-speed)

    def rotate_right(self, speed: float = 0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=0.0, yaw=speed)

    def stop(self):
        if not self.armed:
            raise RuntimeError("Drone is disarmed")
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=0.0, yaw=0.0)
        print("Drone holding position.")
    
    #internal helper 
    def _check_flight(self):
        if not self.armed:
            raise RuntimeError("Drone is disarmed")
        if not self.airborne:
            raise RuntimeError("Drone is on the ground. Take off first.")