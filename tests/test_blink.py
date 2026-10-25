import pytest

from app.vision.blink_detector import BlinkDetector, eye_aspect_ratio


def test_eye_aspect_ratio_for_simple_eye() -> None:
    points = [(0, 0), (1, -1), (3, -1), (4, 0), (3, 1), (1, 1)]
    assert eye_aspect_ratio(points) == pytest.approx(0.5)


def test_single_low_frame_is_not_a_blink() -> None:
    detector = BlinkDetector(0.2, min_closed_frames=2, refractory_seconds=0.1)
    detector.update(0.15, 1.0)
    result = detector.update(0.3, 1.1)
    assert result.blink is False
    assert result.total_blinks == 0


def test_closed_to_open_sequence_counts_one_blink() -> None:
    detector = BlinkDetector(0.2, min_closed_frames=2, refractory_seconds=0.1)
    detector.update(0.15, 1.0)
    detector.update(0.14, 1.05)
    result = detector.update(0.3, 1.1)
    assert result.blink is True
    assert result.total_blinks == 1


def test_closed_frames_do_not_count_repeatedly() -> None:
    detector = BlinkDetector(0.2, min_closed_frames=2, refractory_seconds=0.1)
    for index in range(5):
        result = detector.update(0.1, 1 + index * 0.05)
        assert result.blink is False
    assert detector.update(0.3, 1.3).total_blinks == 1


def test_calibrated_threshold_uses_personal_baseline() -> None:
    detector = BlinkDetector(0.2, 2, 0.1)
    assert detector.set_calibrated_threshold(0.3) == pytest.approx(0.216)


def test_long_eye_closure_is_not_counted_as_a_blink() -> None:
    detector = BlinkDetector(0.2, 2, 0.1, max_closed_seconds=0.5)
    detector.update(0.1, 1.0)
    detector.update(0.1, 1.2)
    result = detector.update(0.3, 1.8)
    assert not result.blink
    assert result.rejected_long_closure
    assert result.total_blinks == 0


def test_blink_retains_minimum_ear_and_duration() -> None:
    detector = BlinkDetector(0.2, 2, 0.1)
    detector.update(0.15, 1.0)
    detector.update(0.09, 1.1)
    result = detector.update(0.3, 1.2)
    assert result.blink
    assert result.minimum_ear == pytest.approx(0.09)
    assert result.closure_duration_seconds == pytest.approx(0.2)
