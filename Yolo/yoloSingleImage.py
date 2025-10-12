from ultralytics import YOLO
import cv2
import logging
from ultralytics.utils import LOGGER

# --- Suppress Ultralytics per-frame "0: 480x640 ..." line ---
class SuppressDetectionLine(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith("0: 480x640")

LOGGER.addFilter(SuppressDetectionLine())
# ------------------------------------------------------------

# Path to your image in Downloads
image_path = r"C:\Users\xxsci\OneDrive\Documents\forVTCRO\Workcell-CV\Workcell-CV\YOLO\FailedImages\172631_mc5dj6xk7.png"
# if you want to test this, replace the "C:\Users\xxsci\OneDrive\Documents\forVTCRO" with wherever you put your repo
model = YOLO(r"C:\Users\xxsci\OneDrive\Documents\forVTCRO\Workcell-CV\Workcell-CV\YOLO\TrainedModles\dataset3_yolo11.pt")
model.conf = 0.7 #model confidence
#right so try using an earlier Yolo version or to train from Ultralytics DO THIS DO THIS

# Run detection on the image (use predict here since it's a single frame)
results = model.predict(source=image_path, conf=0.7, stream=True)

# Load image with OpenCV
image = cv2.imread(image_path)

for result in results:
    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
        # Draw bounding box
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Optional: add class name + confidence
        cls = int(box.cls[0].cpu().numpy())
        conf = float(box.conf[0].cpu().numpy())
        label = f"{model.names[cls]} {conf:.2f}"
        cv2.putText(image, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

# Show the image with bounding boxes
cv2.imshow("Detections", image)
cv2.waitKey(0)
cv2.destroyAllWindows()
