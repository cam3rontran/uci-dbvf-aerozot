# Run full pipeline
# Import necessary modules

#Need to import drone controller and flight firmware layers - richard
#currently problem with having imports in subdirectory

#Example Code:
    
    #initialize firmware and controller
    #firmware = FlightFirmware()
    #controller = DroneController(firmware)

    #mission planning and execution example
    #controller.takeoff()
    #execute_action(controller, detection={"x": 0.5})


def main():
    # Start up system
    # Get camera frame, if it fails use dummy data
    # Runs detection
    # Runs decision logic
    # Executes movement
    # Logs everything
    pass

if __name__ == "__main__":
    main()