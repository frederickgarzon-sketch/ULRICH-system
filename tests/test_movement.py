import numpy as np

from app.vision.movement_analyzer import BodyMovementAnalyzer


def skeleton(offset_x: float = 0, torso_shift: float = 0) -> np.ndarray:
    points = np.zeros((17, 3), dtype=float)
    coordinates = {
        0: (50, 10), 5: (35, 30), 6: (65, 30), 7: (25, 50), 8: (75, 50),
        9: (20, 70), 10: (80, 70), 11: (40 + torso_shift, 65), 12: (60 + torso_shift, 65),
        13: (40, 90), 14: (60, 90), 15: (40, 120), 16: (60, 120),
    }
    for index, (x, y) in coordinates.items():
        points[index] = (x + offset_x, y, 0.95)
    return points


def analyzer() -> BodyMovementAnalyzer:
    return BodyMovementAnalyzer(0.03, 0.015, alpha=1.0, refractory=0.5, posture_threshold=10)


def test_first_pose_establishes_baseline() -> None:
    result = analyzer().update(skeleton(), 1.0, 0.35)
    assert result.magnitude == 0
    assert result.movement_event is False
    assert result.body_scale > 0


def test_translation_is_normalized_and_generates_event() -> None:
    service = analyzer()
    service.update(skeleton(), 1.0, 0.35)
    result = service.update(skeleton(offset_x=10), 2.0, 0.35)
    assert result.magnitude > 0.03
    assert result.movement_event is True
    assert result.total_events == 1


def test_held_motion_does_not_repeat_event() -> None:
    service = analyzer()
    service.update(skeleton(), 1.0, 0.35)
    service.update(skeleton(offset_x=10), 2.0, 0.35)
    result = service.update(skeleton(offset_x=20), 3.0, 0.35)
    assert result.movement_event is False
    assert result.total_events == 1


def test_torso_shift_detects_posture_change() -> None:
    service = analyzer()
    service.update(skeleton(), 1.0, 0.35)
    result = service.update(skeleton(torso_shift=25), 2.0, 0.35)
    assert result.posture_change is True
    assert result.posture_changes == 1


def test_regions_are_reported_separately() -> None:
    service = analyzer()
    service.update(skeleton(), 1.0, 0.35)
    result = service.update(skeleton(offset_x=5), 2.0, 0.35)
    assert set(result.regional) == {"head_shoulders", "left_arm", "right_arm", "torso", "left_leg", "right_leg"}
