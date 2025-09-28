import apriltag
import cv2

cap = cv2.VideoCapture(0) #with laptop webcam

if not cap.isOpened():
	print("Unable to open webcam")
	exit()

img = cv2.imread(cap.cv2.IMREAD_GRAYSCALE)
detector = apriltag.Detector()
result = detector.detect(img)