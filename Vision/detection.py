import cv2
import json
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DUMMY_BOX = (220, 165, 420, 315)  # (x1, y1, x2, y2) centered
LABEL = "DUMMY DETECTION"
LOG_DIR = os.path.join(os.path.dirname(__file__), "detection_logs")

_log_file = None
_entries = []
_entry_count = 0

def init_log():
    global _log_file, _entries, _entry_count
    os.makedirs(LOG_DIR, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_file = os.path.join(LOG_DIR, f"detection_{run_ts}.json")
    _entries = []
    _entry_count = 0

def save_log():
    if _log_file:
        with open(_log_file, "w") as f:
            json.dump(_entries, f, indent=2)

def run_detection(frame):
    global _entry_count
    if frame is None:
        logger.warning("run_detection called with no frame")
        return {"detected": False, "x": None, "y": None}

    x1, y1, x2, y2 = DUMMY_BOX
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    _entry_count += 1
    entry = {
        "entry": _entry_count,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "detected": True,
        "target": {"x": center_x, "y": center_y, "label": LABEL}
    }
    _entries.append(entry)
    save_log()

    logger.info("Detection result: x=%d, y=%d", center_x, center_y)
    return {"detected": True, "x": center_x, "y": center_y}


def draw_detections(frame, detections):
    if not detections["detected"]:
        return frame
    
    x1, y1, x2, y2 = DUMMY_BOX
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, LABEL, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame
