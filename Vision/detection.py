import cv2
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DUMMY_BOX = (220, 165, 420, 315)  # (x1, y1, x2, y2) centered
LABEL = "DUMMY DETECTION"

def run_detection(frame):
    if frame is None:
        logger.warning("run_detection called with no frame")
        return {"detected": False, "x": None, "y": None}
    
    x1, y1, x2, y2 = DUMMY_BOX
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
 
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
