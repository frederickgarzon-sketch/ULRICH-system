from dataclasses import replace

import pytest

from app.tasks import attention_task


def service(monkeypatch):
    monkeypatch.setattr(attention_task, "settings", replace(attention_task.settings, app_mode="real"))
    monkeypatch.setattr(attention_task.session_manager, "_active_id", 901)
    instance = attention_task.AttentionTaskService()
    instance.pair_display()
    return instance


def test_recording_requires_practice(monkeypatch):
    instance = service(monkeypatch)
    with pytest.raises(attention_task.AttentionTaskConflict, match="Complete practice"):
        instance.start()


def test_practice_completion_requires_started_practice(monkeypatch):
    instance = service(monkeypatch)
    with pytest.raises(attention_task.AttentionTaskConflict, match="Start practice"):
        instance.complete_practice()


def test_changed_level_invalidates_practice(monkeypatch):
    instance = service(monkeypatch)
    instance.prepare_practice(task_key="target_tap", age_profile="child", difficulty="easy")
    instance.complete_practice()
    with pytest.raises(attention_task.AttentionTaskConflict, match="Complete practice"):
        instance.start(difficulty="hard")


def test_display_connection_requires_valid_token(monkeypatch):
    instance = service(monkeypatch)
    assert not instance.public_status()["display_connected"]
    assert not instance.validate_display_token("invalid")
    assert not instance.public_status()["display_connected"]
    assert instance.validate_display_token(instance._display_token)
    assert instance.public_status()["display_connected"]
