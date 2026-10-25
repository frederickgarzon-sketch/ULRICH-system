from collections import Counter

from fastapi.testclient import TestClient

from app.main import app
from app.tasks.research_protocols import build_eye_control_plan, protocol_catalog


def test_eye_control_plan_is_reproducible_and_balanced() -> None:
    first = build_eye_control_plan(4217)
    second = build_eye_control_plan(4217)
    assert first == second
    assert len(first) == 33
    assert sum(item["phase"] == "practice" for item in first) == 4
    recorded_saccades = [item for item in first if item["phase"] == "recorded" and item["task_type"] != "fixation"]
    counts = Counter((item["task_type"], item["target_direction"]) for item in recorded_saccades)
    assert counts == {
        ("prosaccade", "left"): 7,
        ("prosaccade", "right"): 7,
        ("antisaccade", "left"): 7,
        ("antisaccade", "right"): 7,
    }


def test_antisaccade_expected_direction_is_opposite() -> None:
    plan = build_eye_control_plan(9)
    for trial in plan:
        if trial["task_type"] == "antisaccade":
            assert trial["expected_direction"] != trial["target_direction"]


def test_protocol_catalog_is_explicit_about_validation() -> None:
    catalog = {item["key"]: item for item in protocol_catalog()}
    eye = catalog["eye_control_standard"]
    assert eye["requires_validated_gaze"] is True
    assert eye["implementation_status"] == "validation_required"
    assert eye["non_diagnostic"] is True


def test_protocol_api_and_gaze_gate() -> None:
    with TestClient(app) as client:
        catalog = client.get("/api/research-tasks/protocols")
        blocked = client.post("/api/research-tasks/start", json={"protocol_key": "eye_control_standard"})
    assert catalog.status_code == 200
    assert any(item["key"] == "eye_control_standard" for item in catalog.json())
    assert blocked.status_code == 409
    assert "monitoring session" in blocked.json()["detail"].lower()
