"""Research feature extraction and guarded composite scoring tests."""

from analysis.hemslnn_features import extract, score


def sample_report() -> dict:
    return {
        "participant": {"age_group": "child"},
        "session": {"duration_seconds": 20.0},
        "attention": {
            "reaction_times": [500, 700],
            "trials": [
                {"time": 5.0, "is_target": True, "missed": True, "false_response": False, "correct": False},
                {"time": 6.7, "is_target": False, "missed": False, "false_response": True, "correct": False},
                {"time": 8.4, "is_target": True, "missed": False, "false_response": False, "correct": True},
            ],
        },
        "attention_configuration": [],
        "blink": {"events": [{"time": 1.0}, {"time": 3.0}, {"time": 6.0}, {"time": 7.0}]},
        "body": {"samples": [{"time": 5.0, "magnitude": 0.1}, {"time": 7.0, "magnitude": 0.3}]},
        "head": {"samples": [
            {"time": 5.0, "yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            {"time": 6.0, "yaw": 1.0, "pitch": 0.0, "roll": 0.0},
        ]},
    }


def test_extracts_attention_movement_and_phase_features() -> None:
    features = extract(sample_report())
    assert features["n_targets"] == 2
    assert features["omission_rate"] == 0.5
    assert features["commission_rate"] == 1.0
    assert round(features["rt_cv"], 3) == 0.167
    assert round(features["attention_span_s"], 1) == 1.7
    assert features["body_mean_task"] == 0.2
    assert features["head_speed_deg_s"] == 1.0
    assert features["head_valid_pct"] == 100.0


def test_score_is_withheld_without_reference_data() -> None:
    result = score(extract(sample_report()), [])
    assert result["status"] == "reference_required"
    assert result["score"] is None
    assert result["minimum_reference_count"] == 30


def test_score_uses_age_matched_reference_and_remains_experimental() -> None:
    features = extract(sample_report())
    references = []
    for index in range(30):
        references.append({
            "age_group": "child",
            "omission_rate": 0.05 + index * 0.003,
            "commission_rate": 0.02 + index * 0.002,
            "rt_cv": 0.10 + index * 0.004,
            "attention_span_s": 30 + index,
            "blink_delta": -3 + index * 0.1,
            "body_mean_task": 0.02 + index * 0.001,
            "head_speed_deg_s": 2 + index * 0.2,
        })
    result = score(features, references)
    assert result["status"] == "experimental_only"
    assert isinstance(result["score"], float)
    assert result["indicators_used"] == 4
    assert result["reference_count"] == 30
