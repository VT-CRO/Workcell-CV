from __future__ import annotations
from typing import List


class CommandAssembler:
    VALID_DIRECTIONS = {"U", "D", "L", "R", "C"}

    def __init__(self) -> None:
        self._buffer: List[str] = []
        self._base_distance: float = 1.0
        self._axis_map = {
            "U": ("Y", 1.0),
            "D": ("Y", -1.0),
            "R": ("X", 1.0),
            "L": ("X", -1.0),
        }

    def set_absolute(self) -> str:
        return self._append_line("G90")

    def set_relative(self) -> str:
        return self._append_line("G91")

    def home(self) -> str:
        return self._append_line("G28")

    def move(self, direction: str, dist_multiplier: float = 1.0) -> str:
        direction_upper = direction.upper()
        if direction_upper not in self.VALID_DIRECTIONS:
            raise ValueError(f"Unsupported direction: {direction}")

        if direction_upper == "C":
            return ""

        axis, sign = self._axis_map[direction_upper]
        move_distance = sign * self._base_distance * dist_multiplier
        move_distance = 0.0 if abs(move_distance) < 1e-12 else move_distance
        line = f"G1 {axis}{self._fmt_float(move_distance)}"
        return self._append_line(line)


    # THIS IS THE OLD WORKING CONSTANT ONE, THE ONE BELOW IS CONSTANT Z LOWERING
    # def zoom_in(self, stage: str) -> str:
    #     calibrateStage = {"S1": 175, "S2": 100, "S3": 25, "calibrated": 0}
    #     stage_key = stage.strip() if stage is not None else ""
    #     if stage_key not in calibrateStage:
    #         upper_key = stage_key.upper()
    #         lower_key = stage_key.lower()
    #         if upper_key in calibrateStage:
    #             stage_key = upper_key
    #         elif lower_key in calibrateStage:
    #             stage_key = lower_key
    #         else:
    #             raise ValueError(f"Unsupported calibration stage: {stage}")
    #     z_value = calibrateStage[stage_key]
    #     line = f"G1 Z{self._fmt_float(z_value)}"
    #     return self._append_line(line)

    def zoom_in(self, height: int) -> int:
        calibrateStage = {"S1": 175, "S2": 100, "S3": 25, "calibrated": 0}
        #stage_key = stage.strip() if stage is not None else ""
        # if stage_key not in calibrateStage:
        #     upper_key = stage_key.upper()
        #     lower_key = stage_key.lower()
        #     if upper_key in calibrateStage:
        #         stage_key = upper_key
        #     elif lower_key in calibrateStage:
        #         stage_key = lower_key
        #     else:
        #         raise ValueError(f"Unsupported calibration stage: {height}")
        # z_value = calibrateStage[stage_key]
        line = f"G1 Z{self._fmt_float(height)}"
        return self._append_line(line)

    def get_program(self) -> str:
        return "\n".join(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def last_line(self) -> str | None:
        return self._buffer[-1] if self._buffer else None

    def _append_line(self, line: str) -> str:
        self._buffer.append(line)
        # print(line, flush=True)
        return line

    def _fmt_float(self, value: float) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:.12g}"


if __name__ == "__main__":
    print("This module is intended to be imported, not run directly.")
