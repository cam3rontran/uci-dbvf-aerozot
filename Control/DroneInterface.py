#Drone Control Module - Top layer

#Last updated: Richard Nguyen - April 25, 2026

#Drone Controller Class and constructor to initialize firmware and states

#include header files eventually for future layers 
from firmware import FlightFirmware 

class DroneController:
    def __init__(self, firmware):
        self.firmware = firmware # we are going to eventually need to build a firmware layer
        self.armed = False
        self.airborne = False

    #primary flight control methods, with basic state checks and calls to firmware layer
    def arm(self):
        self.firmware.arm() #next firmware layer call
        self.armed = True
        print("Armed")

    def disarm(self):
        if self.airborne:
            print("Cannot disarm while airborne.")
            return
        self.firmware.disarm() 
        self.armed = False
        print("Disarmed")

    def takeoff(self):
        if not self.armed:
            self.arm()
        self.firmware.takeoff()
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
    

    #arbritary movement methods with speed params, can change later when dev
    def move_forward(self, speed=0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=speed, roll=0.0, yaw=0.0)

    def move_backward(self, speed=0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=-speed, roll=0.0, yaw=0.0)

    def move_left(self, speed=0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=-speed, yaw=0.0)

    def move_right(self, speed=0.2):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=speed, yaw=0.0)

    def ascend(self, speed=0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5 + speed, pitch=0.0, roll=0.0, yaw=0.0)

    def descend(self, speed=0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5 - speed, pitch=0.0, roll=0.0, yaw=0.0)

    def rotate_left(self, speed=0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=0.0, yaw=-speed)

    def rotate_right(self, speed=0.1):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=0.0, yaw=speed)

    def stop(self):
        self._check_flight()
        self.firmware.apply_movement(throttle=0.5, pitch=0.0, roll=0.0, yaw=0.0)
        print("Drone holding position.")

    #check if drone is in valid state for movement commands
    def _check_flight(self):
        if not self.armed:
            raise RuntimeError("Drone is disarmed")
        if not self.airborne:
            raise RuntimeError("Drone is on the ground. Take off first.")
        
    