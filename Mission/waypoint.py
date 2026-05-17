from enum import Enum
from pathlib import Path


class MarkerType(Enum):
    """Representation for the markers of waypoints"""
    WAYPOINT = 16
    TAKEOFF = 22
    LAND = 21
    HANDOFF_VISION = "VISION"
    HANDOFF_CONTROL = "CONTROL"
    HANDOFF_MISSION = "MISSION"


class Waypoint:
    """This represents a Mission Planner waypoint"""

    def __init__(self, waypoint_id: int,
                 is_home: bool,
                 frame: int,
                 marker_type: MarkerType,
                 delays: list[float],
                 latitude: float,
                 longitude: float,
                 altitude: float):
        self.waypoint_id = waypoint_id
        self.is_home = is_home
        self.frame = frame
        self.marker_type = marker_type
        self.delays = delays
        self.lat = latitude
        self.lon = longitude
        self.alt = altitude


    @staticmethod
    def generate_from(file: str) -> list[Waypoint]:
        """Generate a list from a .waypoints or .txt file, and injections for handoffs from a .handoffs file"""

        file = Path(file)

        handoffs = []

        try:
            handoffs_file = file.parent / f'{file.stem}.handoffs'

            with open(handoffs_file, 'r') as f:
                for line in f:
                    line = line.strip().split()
                    handoff = {(int(line[0])), MarkerType(int(line[1]))}
                    handoffs.append(handoff)
        finally:
            pass

        out = []

        try:
            if not (file.suffix == '.txt' or file.suffix == '.waypoints'): raise FileNotFoundError();

            out = []

            with open(file, 'r') as f:
                for line in f:
                    if line.strip().split()[0] == 'QGC': continue # Start of waypoint; next line

                    components = line.strip().split()
                    waypoint_id = int(components[0])
                    is_home = bool(components[1])
                    frame = int(components[2])
                    marker_type = MarkerType(int(components[3]))
                    delays = [float(x) for x in components[4:8]]
                    latitude = float(components[8])
                    longitude = float(components[9])
                    altitude = float(components[10])

                    if handoffs:
                        if handoffs[0][0] == waypoint_id:
                            out.append(Waypoint(waypoint_id, is_home, frame, marker_type, delays, latitude, longitude,
                                                altitude))
                            out.append(Waypoint(waypoint_id, is_home, frame, handoffs[0][1], delays, latitude, longitude,
                                                altitude))
                            handoffs.pop(0)

                    else:
                        out.append(Waypoint(waypoint_id, is_home, frame, marker_type, delays, latitude, longitude, altitude))

        except FileNotFoundError:
            print("File not found; invalid path!")

        return out