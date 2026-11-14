import pytest

from app.tasks.attention_task import AttentionTaskConflict, AttentionTaskService, score_trial


def test_target_response_is_correct() -> None:
    result = score_trial(is_target=True, responded=True)
    assert result.correct and not result.missed and not result.false_response


def test_missed_target_is_incorrect() -> None:
    result = score_trial(is_target=True, responded=False)
    assert result.incorrect and result.missed


def test_non_target_response_is_false_response() -> None:
    result = score_trial(is_target=False, responded=True)
    assert result.incorrect and result.false_response


def test_non_target_omission_is_correct() -> None:
    result = score_trial(is_target=False, responded=False)
    assert result.correct and not result.incorrect


def test_balloon_plan_contains_complete_reproducible_metadata() -> None:
    import random
    service = AttentionTaskService()
    first = service._build_stimulus_plan(12, 5, "moderate", "target_color", "sky", random.Random(42), practice=False)
    second = service._build_stimulus_plan(12, 5, "moderate", "target_color", "sky", random.Random(42), practice=False)
    assert first == second
    assert {"code", "color", "target_color", "is_target", "x_percent", "y_percent",
            "size_px", "speed", "display_ms", "intertrial_ms", "practice"} <= set(first[0])
    assert all(10 <= item["x_percent"] <= 84 and 14 <= item["y_percent"] <= 58 for item in first)


def test_operator_pause_and_resume_are_explicit_states() -> None:
    import time
    service = AttentionTaskService()
    with pytest.raises(AttentionTaskConflict):
        service.pause()
    service._run_id = 9
    service._last_display_seen = time.monotonic()
    service._display_phase = "recording"
    assert service.pause()["phase"] == "paused"
    assert service.resume()["phase"] == "recording"


def test_balanced_plan_has_exact_targets_and_no_four_consecutive() -> None:
    import random
    plan = AttentionTaskService._balanced_trial_plan(30, 9, random.Random(42))
    assert len(plan) == 30
    assert sum(plan) == 9
    assert "1111" not in "".join("1" if value else "0" for value in plan)
