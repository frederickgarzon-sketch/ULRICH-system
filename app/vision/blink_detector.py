"""Eye Aspect Ratio calculation and closed-to-open blink state machine."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Sequence

Point = tuple[float, float]


def eye_aspect_ratio(points: Sequence[Point]) -> float:
    """Return EAR for six ordered eye points: corners, upper pair, lower pair."""
    if len(points) != 6:
        raise ValueError("EAR requires exactly six eye points")
    horizontal = math.dist(points[0], points[3])
    if horizontal <= 1e-9:
        return 0.0
    vertical_1 = math.dist(points[1], points[5])
    vertical_2 = math.dist(points[2], points[4])
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


@dataclass(frozen=True, slots=True)
class BlinkUpdate:
    blink: bool
    eye_closed: bool
    total_blinks: int
    blinks_per_minute: float
    minimum_ear: float | None = None
    closure_duration_seconds: float = 0.0
    rejected_long_closure: bool = False


class BlinkDetector:
    """Count a blink only after a sustained closed state reopens."""

    def __init__(
        self,
        threshold: float,
        min_closed_frames: int,
        refractory_seconds: float,
        rate_window_seconds: float = 60.0,
        max_closed_seconds: float = 1.5,
    ) -> None:
        if min_closed_frames < 1:
            raise ValueError("min_closed_frames must be at least 1")
        self.threshold = threshold
        self.min_closed_frames = min_closed_frames
        self.refractory_seconds = refractory_seconds
        self.rate_window_seconds = rate_window_seconds
        if max_closed_seconds <= 0:
            raise ValueError("max_closed_seconds must be positive")
        self.max_closed_seconds = max_closed_seconds
        self.closed_frames = 0
        self.closed_started_at: float | None = None
        self.minimum_closed_ear: float | None = None
        self.total_blinks = 0
        self.last_blink_at = float("-inf")
        self.timestamps: deque[float] = deque()

    def update(self, average_ear: float, timestamp: float) -> BlinkUpdate:
        blink = False
        eye_closed = average_ear < self.threshold
        if eye_closed:
            if self.closed_frames == 0:
                self.closed_started_at = timestamp
                self.minimum_closed_ear = average_ear
            else:
                self.minimum_closed_ear = min(float(self.minimum_closed_ear or average_ear), average_ear)
            self.closed_frames += 1
        else:
            closure_duration = max(0.0, timestamp - self.closed_started_at) if self.closed_started_at is not None else 0.0
            valid_sequence = self.closed_frames >= self.min_closed_frames
            rejected_long_closure = valid_sequence and closure_duration > self.max_closed_seconds
            outside_refractory = timestamp - self.last_blink_at >= self.refractory_seconds
            minimum_ear = self.minimum_closed_ear
            if valid_sequence and not rejected_long_closure and outside_refractory:
                blink = True
                self.total_blinks += 1
                self.last_blink_at = timestamp
                self.timestamps.append(timestamp)
            self.closed_frames = 0
            self.closed_started_at = None
            self.minimum_closed_ear = None
        cutoff = timestamp - self.rate_window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()
        observed_window = min(max(timestamp, 1.0), self.rate_window_seconds)
        rate = len(self.timestamps) * 60.0 / observed_window
        if eye_closed:
            closure_duration = max(0.0, timestamp - float(self.closed_started_at or timestamp))
            minimum_ear = self.minimum_closed_ear
            rejected_long_closure = closure_duration > self.max_closed_seconds
        return BlinkUpdate(blink, eye_closed, self.total_blinks, round(rate, 1), minimum_ear,
                           round(closure_duration, 3), rejected_long_closure)

    def set_calibrated_threshold(self, open_eye_baseline: float, ratio: float = 0.72) -> float:
        if open_eye_baseline <= 0:
            raise ValueError("open-eye baseline must be positive")
        self.threshold = open_eye_baseline * ratio
        self.closed_frames = 0
        self.closed_started_at = None
        self.minimum_closed_ear = None
        return self.threshold
