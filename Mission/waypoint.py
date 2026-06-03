from __future__ import annotations

from enum import Enum
from pathlib import Path


class MarkerType(Enum):
    """Waypoint behaviors, valued by their MAVLink MAV_CMD id.

    The numeric values match the command id stored in column 4 of a QGC WPL
    file, so the parser maps them directly.
    """
    WAYPOINT = 16
    LOITER_UNLIM = 17       # MAV_CMD_NAV_LOITER_UNLIM: hold position forever
    LOITER_TURNS = 18       # MAV_CMD_NAV_LOITER_TURNS: orbit N turns
    LOITER_TIME = 19        # MAV_CMD_NAV_LOITER_TIME: hold position for param1 s
    RETURN_TO_LAUNCH = 20   # MAV_CMD_NAV_RETURN_TO_LAUNCH
    LAND = 21               # MAV_CMD_NAV_LAND
    TAKEOFF = 22            # MAV_CMD_NAV_TAKEOFF
    CHANGE_SPEED = 178      # MAV_CMD_DO_CHANGE_SPEED: set cruise speed (param2)


class Waypoint:
    """This represents a Mission Planner waypoint"""

    def __init__(self, waypoint_id: int,
                 is_current: bool,
                 frame: int,
                 marker_type: MarkerType,
                 params: list[float],
                 latitude: float,
                 longitude: float,
                 altitude: float):
        self.waypoint_id = waypoint_id
        self.is_current = is_current  # QGC CURRENT_WP flag (column 1)
        self.frame = frame
        self.marker_type = marker_type
        self.params = params  # PARAM1-4; meaning depends on marker_type
        self.lat = latitude
        self.lon = longitude
        self.alt = altitude

    @property
    def hold_time(self) -> float:
        """Hold/loiter time in seconds (param1 of a Mission Planner waypoint)."""
        return self.params[0] if self.params else 0.0

    @staticmethod
    def generate_from(file: str) -> list[Waypoint]:
        """Generate a waypoint list from a .waypoints or .txt (QGC WPL) file."""

        path = Path(file)

        if path.suffix not in (".txt", ".waypoints"):
            raise ValueError(
                f"Unsupported waypoint file '{path}'; expected .txt or .waypoints"
            )

        out: list[Waypoint] = []

        with open(path, "r") as f:
            for line in f:
                components = line.strip().split()
                if not components:
                    continue  # skip blank lines
                if components[0] == "QGC":
                    continue  # QGC WPL header line

                waypoint_id = int(components[0])

                # QGC WPL line 0 is always the HOME position, not a flyable
                # waypoint. Skip it so we don't issue a spurious leg to home
                # (typically at altitude 0) before takeoff.
                if waypoint_id == 0:
                    continue

                command = int(components[3])
                try:
                    marker_type = MarkerType(command)
                except ValueError:
                    print(
                        f"Skipping waypoint {components[0]}: "
                        f"unsupported command id {command}"
                    )
                    continue

                is_current = bool(int(components[1]))
                frame = int(components[2])
                params = [float(x) for x in components[4:8]]
                latitude = float(components[8])
                longitude = float(components[9])
                altitude = float(components[10])

                out.append(
                    Waypoint(
                        waypoint_id, is_current, frame, marker_type,
                        params, latitude, longitude, altitude,
                    )
                )

        return out
