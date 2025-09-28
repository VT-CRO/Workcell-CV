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

    # Get frame dimensions
    h, w = frame.shape[:2]

    # Define central region (a rectangle around the center)
    margin_x = w // 6   # 1/6 of width on each side
    margin_y = h // 6   # 1/6 of height on each side
    center_x, center_y = w // 2, h // 2

    left_bound   = center_x - margin_x
    right_bound  = center_x + margin_x
    top_bound    = center_y - margin_y
    bottom_bound = center_y + margin_y

    # Draw the central region on screen for visualization
    cv2.rectangle(frame, (left_bound, top_bound), (right_bound, bottom_bound), (255, 0, 0), 2)

    for d in detections:
        pts = d.corners.astype(int)
        cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
        c = tuple(map(int, d.center))
        cv2.putText(frame, f"id:{d.tag_id}", (c[0] - 20, c[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Check if tag center is inside the central region
        if left_bound <= c[0] <= right_bound and top_bound <= c[1] <= bottom_bound:
            print("Tag is centered")
        else:
            if c[0] < left_bound:
                print("Move LEFT")
            elif c[0] > right_bound:
                print("Move RIGHT")
            if c[1] < top_bound:
                print("Move DOWN")
            elif c[1] > bottom_bound:
                print("Move UP")


    cv2.imshow("AprilTag detections", frame)

    # press q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
