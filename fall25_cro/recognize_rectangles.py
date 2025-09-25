import cv2
import numpy as np

image = cv2.imread('nested_rectangles.jpg')

#convert to HSV hue saturation value, for better color detection
hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

#color ranges
color_ranges = {
	'green': [([40, 100, 100], [80, 255, 255])],
	'red': [([0, 150, 150], [10, 255, 255]), ([170, 150, 150], [179, 255, 255])],
	'blue': [([100, 150, 150], [130, 255, 255])],
	'yellow': [([20, 150, 150], [30, 255, 255])]
}

detected_centers = {}

#find colors, find contours, get center.
for color_name, hsv_ranges in color_ranges.items():
	
	combined_mask = None
	
	for lower_hsv, upper_hsv in hsv_ranges:
		lower_bound = np.array(lower_hsv, dtype=np.uint8)
		upper_bound = np.array(upper_hsv, dtype=np.uint8)

		mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
	
		if combined_mask is None:
			combined_mask = mask
		else:
			combined_mask = cv2.bitwise_or(combined_mask, mask)


	#hierarchy information unneeded. RETR_TREE (all) or RETR_EXTERNAL (less data but have what we need)
	contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 

	#find largest contour first
	if contours:
		largest_contour = max(contours, key=cv2.contourArea)
		
		M = cv2.moments(largest_contour)

		# Check if the area is not zero to avoid division by zero error
		if M["m00"] != 0:
			#get center
			cX = int(M["m10"] / M["m00"])
			cY = int(M["m01"] / M["m00"])
		
			#top-left corner of each box is where the text will be written. circle at center
			x_text, y_text, w, h = cv2.boundingRect(largest_contour)

			#store center point
			detected_centers[color_name] = (cX, cY)
			
			#draw on original image VERIFICATION
			# Draw the contour
			cv2.drawContours(image, [largest_contour], -1, (0, 0, 0), 2)
			# Draw the center point
			cv2.circle(image, (cX, cY), 7, (0, 0, 0), -1)
			# Put the color name and coordinates text
			cv2.putText(image, f"{color_name} ({cX}, {cY})", (x_text+10, y_text+20),
			cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

if 'yellow' in detected_centers:
	print("Successfully detected the yellow center")
	print(f"Target Center Coordinates: {detected_centers['yellow']}")
	#logic to move the calibrating head forwards
else:
	print("yellow center not fully detected")


#display image VERIFICATION
cv2.imshow('Detections', image)
cv2.waitKey(0) #close window upon keypress
cv2.destroyAllWindows()