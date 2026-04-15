import cv2

USE_WEBCAM = True #False = video feed
VIDEO_PATH = "sample_video_path.mp4"
DUMMY_BOX = (220, 165, 420, 315) #(x1, y1, x2, y2) centered

def get_source():
    if USE_WEBCAM:
        return cv2.VideoCapture(0)
    else:
        return cv2.VideoCapture(VIDEO_PATH)
    
def draw_detection(frame, box, label):
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame
    
def main():
    #Load sample video/webcam feed
    cap = get_source()

    if not cap.isOpened():
        print("Error: Failed to open video source.")
        return

    print("Running...Press 'q' to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("No frame received. Exiting.")
            break

        #Output dummy detection (fixed bounding box)
        frame = draw_detection(frame, DUMMY_BOX,"DUMMY DETECTION")

        #Display live frames using OpenCV
        cv2.imshow("Drone CV Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
