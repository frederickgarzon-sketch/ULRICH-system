import cv2
import numpy as np
import pytest

from app.vision.head_pose import MODEL_POINTS, POSE_LANDMARK_INDICES, HeadMovementTracker, HeadPose, estimate_head_pose


def make_tracker(alpha: float = 1.0) -> HeadMovementTracker:
    return HeadMovementTracker(alpha, threshold_degrees=12, release_degrees=7, refractory_seconds=0.75)


def test_small_jitter_does_not_count_as_movement() -> None:
    tracker = make_tracker()
    for index, yaw in enumerate([1, -2, 3, -1, 2]):
        result = tracker.update(HeadPose(yaw, 1, 0), 1 + index * 0.1)
    assert result.total_movements == 0
    assert result.direction == "CENTER"


def test_threshold_crossing_counts_once_until_release() -> None:
    tracker = make_tracker()
    first = tracker.update(HeadPose(15, 0, 0), 1.0)
    held = tracker.update(HeadPose(20, 0, 0), 2.0)
    assert first.movement_event is True
    assert first.direction == "RIGHT"
    assert held.movement_event is False
    assert held.total_movements == 1


def test_release_allows_a_later_event() -> None:
    tracker = make_tracker()
    tracker.update(HeadPose(-15, 0, 0), 1.0)
    tracker.update(HeadPose(0, 0, 0), 1.8)
    result = tracker.update(HeadPose(0, -15, 0), 2.6)
    assert result.movement_event is True
    assert result.total_movements == 2
    assert result.direction == "UP"


def test_vertical_direction_matches_calibrated_camera_view() -> None:
    tracker = make_tracker()
    assert tracker.update(HeadPose(0, -15, 0), 1.0).direction == "UP"
    tracker.update(HeadPose(0, 0, 0), 2.0)
    assert tracker.update(HeadPose(0, 15, 0), 3.0).direction == "DOWN"


def test_angle_delta_wraps_across_180_degrees() -> None:
    tracker = make_tracker()
    tracker.set_neutral(yaw=0, pitch=175, roll=0)
    result = tracker.update(HeadPose(0, -175, 0), 1.0)
    assert result.pose.pitch == pytest.approx(10.0)
    assert result.magnitude == pytest.approx(10.0)


def test_neutral_pose_is_subtracted() -> None:
    tracker = make_tracker()
    tracker.set_neutral(yaw=10, pitch=-5, roll=2)
    result = tracker.update(HeadPose(10, -5, 2), 1.0)
    assert result.pose.yaw == pytest.approx(0)
    assert result.pose.pitch == pytest.approx(0)
    assert result.pose.roll == pytest.approx(0)
    assert result.direction == "CENTER"


def test_smoothing_reduces_single_frame_jump() -> None:
    tracker = make_tracker(alpha=0.25)
    tracker.update(HeadPose(0, 0, 0), 1.0)
    result = tracker.update(HeadPose(20, 0, 0), 1.1)
    assert result.pose.yaw == pytest.approx(5.0)
    assert result.movement_event is False


def test_solvepnp_returns_near_frontal_pose_for_projected_model() -> None:
    width, height = 640, 480
    camera = np.array([[width, 0, width / 2], [0, width, height / 2], [0, 0, 1]], dtype=np.float64)
    image_points, _ = cv2.projectPoints(
        MODEL_POINTS, np.zeros((3, 1)), np.array([[0.0], [0.0], [600.0]]), camera, np.zeros((4, 1))
    )
    landmarks = [(0.0, 0.0, 0.0)] * (max(POSE_LANDMARK_INDICES) + 1)
    for index, point in zip(POSE_LANDMARK_INDICES, image_points.reshape(-1, 2)):
        landmarks[index] = (point[0] / width, point[1] / height, 0.0)
    pose = estimate_head_pose(landmarks, width, height)
    assert pose is not None
    assert pose.yaw == pytest.approx(0.0, abs=0.1)
    assert pose.pitch == pytest.approx(0.0, abs=0.1)
    assert pose.roll == pytest.approx(0.0, abs=0.1)
