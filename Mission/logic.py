import Vision
import Control

from pathlib import Path
import json


SPEED = 0.5


class EndExeuction(Exception):
    """A simple breaking exception to raise when the label is None (for now),
    better implementation soon"""

    def __init__():
        pass


def _execute_command(
    controller: Control.DroneInterface.DroneController, label: str
) -> None:
    """Actual meat and potatoes of this, executes the label for what to do
    These will be updated with actual complicated trajectories as needed"""

    if label == "DUMMY_LABEL_1":
        controller.move_forward(SPEED)
    elif label == "DUMMY_LABEL_2":
        controller.move_backward(SPEED)
    elif label == "DUMMY_LABEL_3":
        controller.move_left(SPEED)
    elif label == "DUMMY_LABEL_4":
        controller.move_right(SPEED)
    elif label == "DUMMY_LABEL_5":
        controller.rotate_left()
    elif label == "DUMMY_LABEL_6":
        controller.rotate_right()
    elif label is None:
        controller.land()
        raise EndExeuction


def _debug(log_path: str) -> None:
    """Run module on its own as debug, supply json for offline testing.
    This code isn't ready for usage yet as I need to make it consume
    each line and move to the next!"""

    json_file = Path(log_path)
    json_data = json.loads(json_file)
    command = json_data["target"]["label"]

    _execute_command(command)


if __name__ == "__main__":
    """This method grabs the frame every single tick and represents the main
    execution pipeline"""

    firmware = Control.Firmware()
    controller = Control.DroneInterface.DroneController(firmware)

    controller.arm()
    controller.takeoff()

    # Main execution loop
    try:
        while True:
            json_data = Vision.detection.get_frame()
            command = json_data["target"]["label"]

            _execute_command(command)
    except EndExeuction:
        print("LOG: Finished")
