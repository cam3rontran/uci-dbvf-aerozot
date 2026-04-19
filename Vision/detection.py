import cv2

DUMMY_BOX = (220, 165, 420, 315)  #(x1, y1, x2, y2) centered
label = "DUMMY DETECTION"

def run_detection(frame):
    return [(DUMMY_BOX, label)]

def draw_detections(frame, detections):
    for box, label in detections:
        x1, y1, x2, y2 = box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame
