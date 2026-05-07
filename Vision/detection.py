import cv2
import logging
import os
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Config
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Minimum contour area in pixels to count as a detection
MIN_CONTOUR_AREA = 500

# Ratio range for square detection (perfect square = 1.0)
SQUARE_ASPECT_MIN = 0.75
SQUARE_ASPECT_MAX = 1.25

# Waypoint size classification thresholds (contour area in pixels)
# Placeholder
WAYPOINT_SIZES = {
    "F2_3x3": (500, 3000),
    "F1_7x7": (3000, 10000),
    "LH_15x15": (10000, 30000),
    "WAWM_20x20": (30000, 100000),
}

def run_detection(frame):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if frame is None:
        logger.warning("run_detection called with no frame")
        return {
            "timestamp": timestamp,
            "detected": False,
            "target": None
        }

    x1, y1, x2, y2 = DUMMY_BOX
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    logger.info("[DETECTION] %s | Label: %s | x: %d, y: %d",
            timestamp, LABEL, center_x, center_y)
    return {
        "timestamp": timestamp,
        "detected": True,
        "target": {
            "x": center_x,
            "y": center_y,
            "label": LABEL
        }
    }


def draw_detections(frame, detections):
    if not detections["detected"]:
        return frame
    
    x1, y1, x2, y2 = DUMMY_BOX
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, LABEL, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
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
    


if __name__ == "__main__":
    _dir = os.path.dirname(__file__)

    #Load the Model
    net = cv2.dnn.readNet(os.path.join(_dir, "yolov4-tiny.weights"), os.path.join(_dir, "yolov4-tiny.cfg"))
    with open(os.path.join(_dir, "coco.names"), "r") as f:
        classes = [line.strip() for line in f.readlines()]
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

    #Load and Prepare Image
    img = cv2.imread(os.path.join(_dir, "image.jpg"))
    height, width, _ = img.shape

    #Convert image to 416x416 blob for the network
    blob = cv2.dnn.blobFromImage(img, 1/255.0, (416, 416), (0, 0, 0), swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    #Extract Bounding Boxes, Confidences, and Class IDs
    boxes = []
    confidences = []
    class_ids = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    #Removing redundant overlapping boxes
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    #Final Output
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            label = str(classes[class_ids[i]])
            conf = round(confidences[i], 2)
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(img, f"{label} {conf}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            print(f"Object: {label} | Confidence: {conf} | BBox: [x:{x}, y:{y}, w:{w}, h:{h}]")

    cv2.imshow("Detection", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()