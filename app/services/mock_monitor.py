"""Synthetic live measurements for UI and API development only."""

from __future__ import annotations

import math
import random
import time


class MockMonitor:
    def __init__(self) -> None:
        self.started = time.monotonic()
        self.total_blinks = 0
        self._last_blink_slot = -1

    def snapshot(self) -> dict[str, object]:
        elapsed = time.monotonic() - self.started
        blink_slot = int(elapsed // 3.4)
        if blink_slot > self._last_blink_slot:
            self.total_blinks = max(0, blink_slot)
            self._last_blink_slot = blink_slot
        wave = math.sin(elapsed / 3)
        return {
            "data_mode": "DEMO / MOCK DATA",
            "session_time": round(elapsed, 1),
            "face_camera_status": "MOCK",
            "body_camera_status": "MOCK",
            "face_tracking": True,
            "body_tracking": True,
            "blink_rate": round(16 + math.sin(elapsed / 8) * 2, 1),
            "total_blinks": self.total_blinks,
            "yaw": round(wave * 7, 1),
            "pitch": round(math.cos(elapsed / 4) * 3, 1),
            "roll": round(math.sin(elapsed / 6) * 2, 1),
            "head_movements": int(elapsed // 8),
            "body_movement": round(0.25 + abs(wave) * 0.28, 2),
            "movement_events": int(elapsed // 6),
            "posture_changes": int(elapsed // 25),
            "task_correct": int(elapsed // 12),
            "task_incorrect": int(elapsed // 45),
            "task_missed": int(elapsed // 60),
            "task_accuracy": round(85 + random.uniform(-1, 1), 1),
            "reaction_time_ms": round(610 + math.sin(elapsed / 5) * 35),
        }


mock_monitor = MockMonitor()

