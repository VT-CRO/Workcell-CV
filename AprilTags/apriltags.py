import pupil_apriltags
import cv2
import numpy as np

cap = cv2.VideoCapture(0) #with laptop webcam

if not cap.isOpened():
	print("Unable to open webcam")
	exit()

#up down left right

while True:
	ret, frame = cap.read()
	if not ret:
		print("Can't read frames")
		break

	#convert to HSV hue saturation value, for better color detection
	hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


	#display frame VERIFICATION
	cv2.imshow('Detections', frame)
    #0xFF avoids errors on some computers according to google
	key = cv2.waitKey(1) & 0xFF 


	if key == ord('q'): 
		break
	elif key == ord(' '):
		stage_index += (1-int(stage_index / 3)) #done so that if stage_index is the final stage it won't try to go to nonexistent conseq. states
		print("Advancing to next stage.")



#when all else done
cap.release()
cv2.destroyAllWindows()