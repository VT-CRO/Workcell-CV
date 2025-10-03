import asyncio
import cv2
import time
import math
from dataclasses import dataclass
from typing import Tuple

from commandAssembler import CommandAssembler
from enderTalker import CameraController
from pupil_apriltags import Detector


@dataclass
class TargetRegion:
    top: int
    bottom: int
    left: int
    right: int
    center_x: int
    center_y: int


class AutoCalibrator:
    def __init__(
        self,
        camera_index: int = 1,
        target_scale: float = 0.1,
        scale_step_fraction: float = 0.05,
        min_scale: float = 0.05,
        max_scale: float = 0.9,
        dist_weight: float = 0.8,
        size_weight: float = 0.2,
    ) -> None:
        self.camera_index = camera_index
        self.target_scale = target_scale
        self.scale_step_fraction = scale_step_fraction
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.dist_weight = dist_weight
        self.size_weight = size_weight
        self.detector = Detector(families="tag36h11")
        self.command_assembler = CommandAssembler()
        self.printer = CameraController()
        self._loop = asyncio.new_event_loop()
        self.cap = None

        # Key codes from cv2.waitKeyEx for arrow input
        self.UP_ARROW = 2490368
        self.DOWN_ARROW = 2621440

        # Calibration staging
        self.calibration_stages = ["S1", "S2", "S3", "calibrated"]
        self.stage_index = 0
        self.consecutive_center = 0
        self.stage_announced = False
        self.calibration_complete = False

    def run(self) -> None:
        if self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        if not self._ensure_printer_connected():
            self._cleanup_printer()
            return

        self._initialize_printer_position()

        self.cap = self._open_camera()
        try:
            while True:
                self._ensure_stage_announced()
                if self.calibration_complete:
                    break

                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to grab frame")
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detections = self.detector.detect(gray)

                region = self._calculate_target_region(frame.shape[:2])
                self._draw_target_region(frame, region)

                command_label = self._process_detections(frame, detections, region)
                if self.calibration_complete:
                    continue

                self._draw_overlay(frame, command_label)

                cv2.imshow("AprilTag detections", frame)

                if not self._handle_key(cv2.waitKeyEx(1)):
                    break
        finally:
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            self._cleanup_printer()

    def _run_async(self, coro):
        return self._loop.run_until_complete(coro)

    def _ensure_printer_connected(self) -> bool:
        if self.printer.running:
            return True
        try:
            return bool(self._run_async(self.printer.connect()))
        except Exception as exc:
            print(f"Printer connection failed: {exc}")
            return False

    def _initialize_printer_position(self) -> None:
        self._send_gcode(self.command_assembler.home(), wait_completion=True)
        self._send_gcode(self.command_assembler.set_relative())

    def _send_gcode(self, gcode: str, wait_completion: bool = False) -> None:
        if not gcode:
            return
        script = f"{gcode}\nM400" if wait_completion else gcode
        try:
            self._run_async(self.printer.send_gcode(script))
        except Exception as exc:
            print(f"Failed to send G-code '{gcode}': {exc}")

    def _cleanup_printer(self) -> None:
        if self._loop.is_closed():
            return
        if self.printer.running:
            try:
                self._run_async(self.printer.disconnect())
            except Exception as exc:
                print(f"Printer disconnect failed: {exc}")
        self._loop.close()

    def _open_camera(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open camera index {self.camera_index}")
        return cap

    def _calculate_target_region(self, frame_shape: Tuple[int, int]) -> TargetRegion:
        frame_height, frame_width = frame_shape
        target_side = max(1, int(min(frame_width, frame_height) * self.target_scale))
        half_side = target_side // 2
        center_x = frame_width // 2
        center_y = frame_height // 2
        top = max(0, center_y - half_side)
        bottom = min(frame_height, center_y + half_side)
        left = max(0, center_x - half_side)
        right = min(frame_width, center_x + half_side)
        return TargetRegion(top=top, bottom=bottom, left=left, right=right, center_x=center_x, center_y=center_y)

    def _draw_target_region(self, frame, region: TargetRegion) -> None:
        cv2.rectangle(frame, (region.left, region.top), (region.right, region.bottom), (0, 0, 255), 2)

    def _process_detections(self, frame, detections, region: TargetRegion) -> str:
        command_label = "No tag detected"
        for detection in detections:
            pts = detection.corners.astype(int)
            tag_center_x, tag_center_y = detection.center

            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            center_point = (int(tag_center_x), int(tag_center_y))
            cv2.circle(frame, center_point, 4, (0, 255, 255), -1)
            cv2.putText(
                frame,
                f"id:{detection.tag_id}",
                (center_point[0] - 20, center_point[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            command = self._determine_command(tag_center_x, tag_center_y, region)
            multiplier = self._compute_distance_multiplier(pts, center_point, region)

            self._emit_command(command, multiplier)
            self._handle_command_for_stage(command)
            command_label = f"Cmd: {command}"

            if self.calibration_complete:
                break

        return command_label

    def _determine_command(self, tag_center_x: float, tag_center_y: float, region: TargetRegion) -> str:
        vertical_distance = 0
        vertical_command = ""
        if tag_center_y < region.top:
            vertical_distance = region.top - tag_center_y
            vertical_command = "U"
        elif tag_center_y > region.bottom:
            vertical_distance = tag_center_y - region.bottom
            vertical_command = "D"

        horizontal_distance = 0
        horizontal_command = ""
        if tag_center_x < region.left:
            horizontal_distance = region.left - tag_center_x
            horizontal_command = "L"
        elif tag_center_x > region.right:
            horizontal_distance = tag_center_x - region.right
            horizontal_command = "R"

        if vertical_distance == 0 and horizontal_distance == 0:
            return "C"
        if vertical_distance >= horizontal_distance and vertical_command:
            return vertical_command
        return horizontal_command or vertical_command or "C"

    def _compute_distance_multiplier(self, pts, center_point, region: TargetRegion) -> float:
        dist_tag_center = math.dist((region.center_x, region.center_y), center_point)
        tag_size = math.dist((pts[0][0], pts[0][1]), (pts[2][0], pts[2][1]))

        if dist_tag_center > 250:
            dist_scale = 5
        elif dist_tag_center < 50:
            dist_scale = 0.1
        else:
            dist_scale = dist_tag_center / 50

        multiplier = (dist_scale * self.dist_weight) + ((1 - (tag_size / 200)) * self.size_weight)
        return max(multiplier, 0.5)

    def _emit_command(self, command: str, multiplier: float) -> None:
        gcode_line = self.command_assembler.move(command, multiplier)
        if gcode_line:
            self._send_gcode(gcode_line)
        time.sleep(0.1)

    def _handle_command_for_stage(self, command: str) -> None:
        if self.calibration_complete:
            return
        if command == "C":
            self.consecutive_center += 1
        else:
            self.consecutive_center = 0
        if self.consecutive_center >= 5:
            self._advance_stage()

    def _draw_overlay(self, frame, command_label: str) -> None:
        frame_height = frame.shape[0]
        cv2.putText(
            frame,
            command_label,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            f"Target size: {self.target_scale * 100:.1f}% of min dim",
            (10, frame_height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )

    def _handle_key(self, key: int) -> bool:
        if key == -1:
            return True
        if key == ord("q"):
            return False
        if key == self.UP_ARROW:
            self.target_scale = min(self.target_scale * (1 + self.scale_step_fraction), self.max_scale)
        elif key == self.DOWN_ARROW:
            self.target_scale = max(self.target_scale * (1 - self.scale_step_fraction), self.min_scale)
        return True

    def _ensure_stage_announced(self) -> None:
        if self.stage_announced:
            return
        stage = self.calibration_stages[self.stage_index]
        self._send_gcode(self.command_assembler.set_absolute())
        self._send_gcode(self.command_assembler.zoom_in(stage), wait_completion=True)
        self._send_gcode(self.command_assembler.set_relative())
        if stage == "calibrated":
            self.calibration_complete = True
            self.stage_announced = True
            return
        if stage != "S1":
            self.target_scale = max(self.target_scale * 0.5, self.min_scale)
        self.consecutive_center = 0
        self.stage_announced = True

    def _advance_stage(self) -> None:
        if self.stage_index < len(self.calibration_stages) - 1:
            self.stage_index += 1
            self.stage_announced = False
            self.consecutive_center = 0
            if self.calibration_stages[self.stage_index] == "calibrated":
                self.calibration_complete = True
        else:
            self.calibration_complete = True


def main() -> None:
    calibrator = AutoCalibrator()
    calibrator.run()


if __name__ == "__main__":
    main()
