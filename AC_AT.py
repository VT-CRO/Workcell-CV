import cv2
import time
import asyncio
from pupil_apriltags import Detector
from enderTalker import CameraController
import math

Eddie = CameraController()

async def run():

    await Eddie.connect()
    await Eddie.set_relative()

    CAMERA_INDEX = 1

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"Unable to open camera index {CAMERA_INDEX}")
        exit()

    detector = Detector(families="tag36h11")

    target_scale = 0.2
    scale_step_fraction = 0.05
    min_scale = 0.05
    max_scale = 0.9
    distMultipler = 1

    UP_ARROW = 2490368
    DOWN_ARROW = 2621440

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = detector.detect(gray)

        frame_height, frame_width = frame.shape[:2]
        target_side = max(1, int(min(frame_width, frame_height) * target_scale))
        half_side = target_side // 2
        center_x = frame_width // 2
        center_y = frame_height // 2
        top = max(0, center_y - half_side)
        bottom = min(frame_height, center_y + half_side)
        left = max(0, center_x - half_side)
        right = min(frame_width, center_x + half_side)

        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        command_text = "No tag detected"

        for d in detections:
            pts = d.corners.astype(int)
            tag_center_x, tag_center_y = d.center
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            center_point = (int(tag_center_x), int(tag_center_y))
            cv2.circle(frame, center_point, 4, (0, 255, 255), -1)
            cv2.putText(frame, f"id:{d.tag_id}", (center_point[0] - 20, center_point[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            vertical_distance = 0
            vertical_command = ""
            if tag_center_y < top:
                vertical_distance = top - tag_center_y
                vertical_command = "U"
            elif tag_center_y > bottom:
                vertical_distance = tag_center_y - bottom
                vertical_command = "D"

            horizontal_distance = 0
            horizontal_command = ""
            if tag_center_x < left:
                horizontal_distance = left - tag_center_x
                horizontal_command = "L"
            elif tag_center_x > right:
                horizontal_distance = tag_center_x - right
                horizontal_command = "R"

            if vertical_distance == 0 and horizontal_distance == 0:
                command = "C"
            elif vertical_distance >= horizontal_distance and vertical_command:
                command = vertical_command
            else:
                command = horizontal_command or vertical_command or "C"

            print(
                f"Tag {d.tag_id}: center=({tag_center_x:.1f}, {tag_center_y:.1f}) command={command}",
                flush=True,
            )

            distMultipler = target_scale

            await Eddie.send_command(command, distMultipler)
            time.sleep(0.1)

            if command_text == "No tag detected":
                command_text = f"Cmd: {command}"

        cv2.putText(frame, command_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Target size: {target_scale * 100:.1f}% of min dim", (10, frame_height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("AprilTag detections", frame)

        key = cv2.waitKeyEx(1)
        if key == ord("q"):
            break
        elif key == UP_ARROW:
            target_scale = min(target_scale * (1 + scale_step_fraction), max_scale)
        elif key == DOWN_ARROW:
            target_scale = max(target_scale * (1 - scale_step_fraction), min_scale)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(run())
