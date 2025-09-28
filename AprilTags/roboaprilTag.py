import cv2
from pupil_apriltags import Detector

cap = cv2.VideoCapture(0)  # open webcam
if not cap.isOpened():
    print("Unable to open webcam")
    exit()

detector = Detector(families="tag36h11")  # use correct family

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    detections = detector.detect(gray)
    print(f"Found {len(detections)} tag(s)")

    for d in detections:
        pts = d.corners.astype(int)
        cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
        c = tuple(map(int, d.center))
        cv2.putText(frame, f"id:{d.tag_id}", (c[0] - 20, c[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("AprilTag detections", frame)

    # press q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
