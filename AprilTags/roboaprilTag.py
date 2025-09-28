import cv2
import numpy as np
import robotpy_apriltag as apriltag

# Create detector with default family ("tag36h11" is standard for FRC)
options = apriltag.DetectorOptions(families="tag36h11")
detector = apriltag.Detector(options)

# Load a grayscale image (from camera or file)
image = cv2.imread("example.png", cv2.IMREAD_GRAYSCALE)

# Run detection
results = detector.detect(image)

for r in results:
    print(f"Detected tag {r.tag_id} with corners {r.corners}")

# Example camera intrinsics (fx, fy, cx, cy)
fx, fy = 600, 600
cx, cy = 320, 240
tag_size = 0.165  # meters (16.5 cm for FRC tags)

pose, e0, e1 = detector.detection_pose(results[0], (fx, fy, cx, cy), tag_size)

print("Rotation matrix:\n", pose[0])
print("Translation vector:\n", pose[1])
