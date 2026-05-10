import cv2
import logging
import os
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

#config
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

#min contour area in pixels to count as a detection
MIN_CONTOUR_AREA = 500

#ratio range for square detection (perfect square = 1.0)
SQUARE_ASPECT_MIN = 0.75
SQUARE_ASPECT_MAX = 1.25

#waypoint size classification thresholds (contour area in pixels)
#placeholders
WAYPOINT_SIZES = {
    "F2_3x3": (500, 3000),
    "F1_7x7": (3000, 10000),
    "LH_15x15": (10000, 30000),
    "WAWM_20x20": (30000, 100000),
}

def run_detection(frame, target_waypoint=None, color_lower=None, color_upper=None):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 
    if frame is None:
        logger.warning("run_detection called with no frame")
        return {
            "timestamp": timestamp,
            "detected": False,
            "target": None
        }
 
    #preprocess the frame
    processed = _preprocessor.preprocess(frame)
 
    waypoint = detect_waypoint(processed, target_waypoint, color_lower, color_upper)
 
    if waypoint:
        logger.info("[DETECTION] %s | Looking for: %s | Found: %s | x=%d, y=%d | Area=%d | Aspect=%.2f",
                    timestamp, target_waypoint or "any", waypoint["label"],
                    waypoint["x"], waypoint["y"], waypoint["area"], waypoint["aspect_ratio"])
        return {
            "timestamp": timestamp,
            "detected": True,
            "target": {
                "x": waypoint["x"],
                "y": waypoint["y"],
                "label": waypoint["label"],
                "bounding_rect": waypoint["bounding_rect"]
            }
        }
 
    logger.info("[NO TARGET] %s | Looking for: %s", timestamp, target_waypoint or "any")
    return {
        "timestamp": timestamp,
        "detected": False,
        "target": None
    }

def draw_detections(frame, detections):
 
    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
 
    #frame center crosshair
    center_x = FRAME_WIDTH // 2
    center_y = FRAME_HEIGHT // 2
    cv2.drawMarker(frame, (center_x, center_y),
                   (255, 255, 255), cv2.MARKER_CROSS, 20, 1)
 
    if not detections["detected"]:
        cv2.putText(frame, "NO TARGET", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame
 
    target = detections["target"]
    tx, ty = target["x"], target["y"]
 
    #green bounding rectangle 
    if "bounding_rect" in target:
        bx, by, bw, bh = target["bounding_rect"]
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        cv2.putText(frame, target["label"], (bx, by - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    else:
        #label near the center if no bounding rect
        cv2.putText(frame, target["label"], (tx + 15, ty - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
 
    #center marking
    cv2.line(frame, (tx - 15, ty), (tx + 15, ty), (0, 0, 255), 1)
    cv2.line(frame, (tx, ty - 15), (tx, ty + 15), (0, 0, 255), 1)
 
    #offset from frame center
    offset_x = tx - center_x
    offset_y = ty - center_y
    cv2.putText(frame, f"Offset: ({offset_x}, {offset_y})", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
 
    return frame
 

class ImagePreprocessor:
    """Handles all frame preprocessing before detection"""
 
    def __init__(self, target_size=(FRAME_WIDTH, FRAME_HEIGHT)):
        self.target_size = target_size
 
    def preprocess(self, frame):
        """Apply full preprocessing pipeline."""
        # Resize
        processed = cv2.resize(frame, self.target_size)
 
        # Denoise using Gaussian blur
        processed = cv2.GaussianBlur(processed, (5, 5), 0)
 
        # Enhance contrast using CLAHE
        lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
 
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)
 
        enhanced = cv2.merge([l_enhanced, a, b])
        frame = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
 
        return frame
    
_preprocessor = ImagePreprocessor()

def detect_edges_sobel(frame):
    """Sobel edge detection on greyscale frame"""
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    grey = cv2.GaussianBlur(grey, (5, 5), 0)

    #vertical edges
    sobel_x = cv2.Sobel(grey, cv2.CV_64F, 1, 0, ksize=3)

    #horizontal edges
    sobel_y = cv2.Sobel(grey, cv2.CV_64F, 0, 1, ksize=3)

    #total edge strength
    edges = cv2.magnitude(sobel_x, sobel_y)

    #normalize back
    edges = np.uint8(np.clip(edges, 0, 255))

    return edges

def filter_squares(contours):
    squares = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < MIN_CONTOUR_AREA:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        #check fpr 4 vertices
        if len(approx) != 4:
            continue

        #check ratio
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 0

        if SQUARE_ASPECT_MIN < aspect_ratio < SQUARE_ASPECT_MAX:
            squares.append({
                "contour": contour,
                "approx": approx,
                "area": area,
                "aspect_ratio": round(aspect_ratio, 2),
                "bounding_rect": (x, y, w, h)
            })
    squares.sort(key=lambda s: s["area"], reverse=True)
    return squares

def detect_by_color(frame, color_lower, color_upper):
    #change RGB values to HSV values
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    #determine color of interest and make it white and everything else black
    mask = cv2.inRange(hsv, color_lower, color_upper)

    #return the mask to analyze for waypoints
    return mask

def classify_waypoint(area):
    """Classify waypoint type based on contour area (backup)"""
    for label, (min_area, max_area) in WAYPOINT_SIZES.items():
        if min_area <= area <= max_area:
            return label
    return "unknown"

def detect_waypoint(frame, target_waypoint=None, color_lower=None, color_upper=None):
    """full detection pipeline"""
    color_mask = detect_by_color(frame, color_lower, color_upper)
    edges = detect_edges_sobel(frame)
 
    #keep only edges inside the colored region
    combined = cv2.bitwise_and(edges, edges, mask=color_mask)
    _, binary = cv2.threshold(combined, 50, 255, cv2.THRESH_BINARY)
 
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
 
    squares = filter_squares(contours)
    if not squares:
        return None
 
    if target_waypoint and target_waypoint in WAYPOINT_SIZES:
        min_area, max_area = WAYPOINT_SIZES[target_waypoint]
        matches = [s for s in squares if min_area <= s["area"] <= max_area]
 
        if not matches:
            return None
 
        #pick closest to expected size midpoint
        expected_mid = (min_area + max_area) / 2
        best = min(matches, key=lambda s: abs(s["area"] - expected_mid))
    else:
        #use largest if no target specified
        best = squares[0]
 
    #calculate center
    M = cv2.moments(best["contour"])
    if M["m00"] == 0:
        return None
 
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
 
    label = target_waypoint if target_waypoint else classify_waypoint(best["area"])
 
    return {
        "x": cx,
        "y": cy,
        "label": label,
        "area": best["area"],
        "aspect_ratio": best["aspect_ratio"],
        "bounding_rect": best["bounding_rect"]
    }
