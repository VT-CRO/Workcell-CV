import cv2
import numpy as np

cap = cv2.VideoCapture(0) #with laptop webcam

if not cap.isOpened():
	print("Unable to open webcam")
	exit()

#color ranges. tuned to fit how it looks on my phone. may need adjustment for paper strips. HUE SATURATION VALUE.
color_ranges = {
	'green': [([50, 80, 100], [90, 255, 255])],
	'red': [([0, 100, 120], [10, 255, 255]), ([170, 150, 150], [179, 255, 255])],
	'blue': [([100, 80, 120], [130, 255, 255])],
	'yellow': [([17, 20, 100], [35, 255, 255])]
}

detection_stages = ['green', 'red', 'blue', 'yellow']
stage_index = 0

while True:
	ret, frame = cap.read()
	if not ret:
		print("Can't read frames")
		break

	#convert to HSV hue saturation value, for better color detection
	hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

	detected_centers = {}
	target_color = detection_stages[stage_index]
	hsv_ranges = color_ranges[target_color]

	#find colors, find contours, get center.
	
	combined_mask = None

	for lower_hsv, upper_hsv in hsv_ranges:
		lower_bound = np.array(lower_hsv, dtype=np.uint8)
		upper_bound = np.array(upper_hsv, dtype=np.uint8)

		mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)
	
		if combined_mask is None:
			combined_mask = mask
		else:
			combined_mask = cv2.bitwise_or(combined_mask, mask)

	#hierarchy information unneeded
	contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	
	target_detected = False

	#find largest contour first
	if contours:
		largest_contour = max(contours, key=cv2.contourArea)
		
		
		# to prevent tiny color detected boxes in the wrong places.
		if cv2.contourArea(largest_contour) > 500: # Area threshold

			target_detected = True
			M = cv2.moments(largest_contour)
				# Check if the area is not zero to avoid division by zero error
			if M["m00"] != 0:
				#get center
				cX = int(M["m10"] / M["m00"])
				cY = int(M["m01"] / M["m00"])
	
				#top-left corner of each box is where the text will be written. circle at center
				x_text, y_text, w, h = cv2.boundingRect(largest_contour)

				#store center point
				detected_centers[target_color] = (cX, cY)
		
				#draw on original frame VERIFICATION
				# Draw the contour
				cv2.drawContours(frame, [largest_contour], -1, (0, 0, 0), 2)
			
				# Draw the center point, label what color's center it is.
				cv2.circle(frame, (cX, cY), 3, (0, 0, 0), -1)
				cv2.putText(frame, f"{target_color} ({cX}, {cY})", (cX+15, cY),
				cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
				# Put the color name and coordinates text
				cv2.putText(frame, f"{target_color} ({cX}, {cY})", (x_text+15, y_text+15),
				cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

	if target_detected:
		print(f"Target '{target_color}' DETECTED.")
		#logic to move the calibrating head forwards will go here eventually
	else:
		print(f"Target '{target_color}' MISSING")


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