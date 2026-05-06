import cv2
import logging
import os
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DUMMY_BOX = (220, 165, 420, 315)  # (x1, y1, x2, y2) centered
LABEL = "DUMMY DETECTION"

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