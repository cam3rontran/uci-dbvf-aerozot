# Visual Anchoring Flow

How the Mission module fine-positions the drone onto a **physical** waypoint
detected by the camera, after GPS has gotten it close.

## Why

GPS navigation lands the drone within an acceptance radius (~1.5 m) of a
waypoint's coordinates — good enough to *arrive*, not to *anchor*. Many missions
need the drone centered over a physical marker (a painted square, a pad, a
target). That last meter is closed visually:

- **Vision** sees where the marker is in the camera frame.
- **Control** turns that offset into a fine movement (which way, how far/long).
- **Mission** runs the loop and commands the drone.

## Responsibility split

Mission **orchestrates only**. It implements neither detection nor the movement
math — those live in Vision and Control respectively. Mission owns the loop, the
`Drone`, and the contract the other two implement.

| Concern | Owner | Where |
|---------|-------|-------|
| Grab a camera frame | Camera | `Camera.get_frame()` |
| Detect the physical waypoint in the frame | Vision | `VisionDetector.run_detection(frame)` |
| Compute the corrective move (direction + duration) | Control | `AnchorController.anchor_command(detection)` |
| Run the loop, execute the move, decide when done | **Mission** | `DroneNavigator._anchor_to_waypoint(wp)` |
| Send body-frame velocity to the autopilot | Drone | `Drone.move_for_duration(...)` |

## Hook contract (`Protocol`s in `logic.py`)

These are runtime-checkable `typing.Protocol`s, so Vision/Control satisfy them by
structure — no imports or base classes required, and Mission stays decoupled.

```python
class Camera(Protocol):
    def get_frame(self) -> object | None: ...
    # latest camera frame, or None if unavailable

class VisionDetector(Protocol):
    def run_detection(self, frame) -> dict | None: ...
    # dict with at least {"detected": bool}; when detected, also the
    # waypoint's image-space offset for Control to act on

class AnchorController(Protocol):
    def anchor_command(
        self, detection: dict
    ) -> tuple[tuple[float, float, float], float, float] | None: ...
    # (direction, speed_m_s, duration_s) where direction is body-frame
    # (forward, right, down); or None once the drone is anchored/centered
```

## The loop

`DroneNavigator._anchor_to_waypoint(wp)` runs after `_fly_to(wp)` for every
`WAYPOINT`. Pseudocode of what Mission does:

```
if no vision or no control:        # not configured
    return                         # GPS arrival is final

repeat up to ANCHOR_MAX_ITERATIONS:
    frame     = camera.get_frame()           if camera else None
    detection = vision.run_detection(frame)   # HOOK: Vision
    if not detection.detected:
        return                                # nothing to anchor onto
    command   = control.anchor_command(detection)   # HOOK: Control
    if command is None:
        return                                # Control says: anchored ✓
    direction, speed, duration = command
    drone.move_for_duration(direction, speed, duration)
# budget exhausted -> give up, continue mission
```

See `anchor_sequence.svg` for the full sequence diagram.

## Termination

The loop ends on any of:

1. **Anchored** — `anchor_command` returns `None` (Control judges it centered).
2. **Nothing detected** — Vision returns `detected: False`; Mission skips and
   continues (GPS arrival stands).
3. **Budget exhausted** — `ANCHOR_MAX_ITERATIONS` (default 10) corrections made
   without converging; Mission logs and moves on rather than hovering forever.

## Configuration

Anchoring is opt-in via constructor injection — nothing changes for GPS-only
missions:

```python
from drone import Drone
from logic import DroneNavigator
import waypoint
# import Vision, Control   # supplied by those teams

drone = Drone("udp:127.0.0.1:14550")
wps   = waypoint.Waypoint.generate_from("mission.waypoints")

navigator = DroneNavigator(
    drone, wps,
    camera=Vision.Camera(),          # implements Camera
    vision=Vision,                   # module implements VisionDetector
    control=Control.Anchorer(drone), # implements AnchorController
)
navigator.main()
```

Omit `camera`/`vision`/`control` and the anchor step is a no-op.

Tunable: `ANCHOR_MAX_ITERATIONS` in `logic.py`.

## Notes & open items

- Anchoring currently triggers on `WAYPOINT` arrivals only. If a specific marker
  type should gate it instead, that's a Mission-side change (the trigger
  condition in `_consume_waypoint`), not a schema change.
- `move_for_duration` is open-loop on the *move* itself; precision comes from the
  outer Vision→Control feedback loop re-evaluating after each correction.
- Mission never calls Vision/Control APIs by concrete name beyond this contract;
  if their signatures differ, adapt at the injection site, not inside Mission.
