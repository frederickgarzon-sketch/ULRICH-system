import pytest

from app.services.landmark_config import snapshot, validate_selection


def test_default_landmark_configuration_is_versioned_and_hashed() -> None:
    config = snapshot()
    assert config["schema_version"] == "landmarks-1.0"
    assert config["fixed_feature_order"] is True
    assert len(config["configuration_hash"]) == 16


def test_landmark_dependencies_reject_invalid_normalized_movement() -> None:
    with pytest.raises(ValueError, match="Normalized movement"):
        validate_selection("eyes", "eyes", "", "", "normalized_movement")


def test_valid_core_landmark_selection() -> None:
    validate_selection("eyes,head_pose", "eyes,head_pose", "head_shoulders,torso",
                       "head_shoulders,torso", "angle,frequency,normalized_movement")
