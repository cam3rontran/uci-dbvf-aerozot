import cv2

USE_WEBCAM = True #False = video feed
VIDEO_PATH = "sample_video_path.mp4"

def get_source():
    if USE_WEBCAM:
        return cv2.VideoCapture(0)
    else:
        return cv2.VideoCapture(VIDEO_PATH)
    
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

        #Display live frames using OpenCV
        cv2.imshow("Drone CV Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
