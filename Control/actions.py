#actions.py will be for actual decision making in missions - seperate from drone state
# Last updated: Richard Nguyen April 25, 2026


def decider(detection=None):
    if detection is None:
        return "SEARCH"

    x_position = detection.get("x", 0.0)

    if x_position < -0.1:
        return "MOVE_LEFT"
    elif x_position > 0.1:
        return "MOVE_RIGHT"
    else:
        return "MOVE_FORWARD"
    

def execute_action(controller, detection=None):
    if not controller.armed or not controller.airborne:
        print("Cannot execute action: drone is not armed and airborne.")
        return

    decision = decider(detection)
    print(f"Decision: {decision}")

    if decision == "MOVE_FORWARD":
        controller.move_forward()
    elif decision == "MOVE_LEFT":
        controller.move_left()
    elif decision == "MOVE_RIGHT":
        controller.move_right()
    elif decision == "STOP":
        controller.stop()
    elif decision == "SEARCH":
        controller.rotate_right()