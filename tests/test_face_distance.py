import pytest

from app.vision.face_distance import distance_quality, estimate_face_distance_cm


def eyes(center_x: float) -> list[tuple[float, float]]:
    return [(center_x, 0.5)] * 6


def test_estimated_distance_uses_apparent_eye_spacing() -> None:
    near = estimate_face_distance_cm(eyes(0.35), eyes(0.65), 640, 480)
    far = estimate_face_distance_cm(eyes(0.44), eyes(0.56), 640, 480)
    assert near is not None and far is not None
    assert near < far


@pytest.mark.parametrize(("distance", "expected"), [(20, "red"), (30, "yellow"), (40, "green"), (55, "yellow"), (70, "red")])
def test_distance_quality_bands(distance: float, expected: str) -> None:
    assert distance_quality(distance)[0] == expected
