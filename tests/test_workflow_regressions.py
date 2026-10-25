"""Isolated regression tests; never use the live participant database/cameras."""
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.repository import repository
from app.services.access_control import COOKIE_NAME, Identity, issue_token, token_hash
from app.sessions.session_manager import session_manager
from app.tasks.attention_task import AttentionTaskService, AttentionTaskConflict, attention_task_service
from app.services import body_analysis_service as body_module
from app.services import face_analysis_service as face_module
from app.database.database import initialize_database


@pytest.fixture(autouse=True)
def initialized_database():
    initialize_database()


def test_cancel_practice_does_not_unlock_recording(monkeypatch):
    monkeypatch.setattr(session_manager, '_active_id', 741)
    service = AttentionTaskService(); service.pair_display()
    service.prepare_practice(task_key='target_tap', age_profile='child', difficulty='easy')
    assert service.cancel_practice()['phase'] == 'waiting'
    with pytest.raises(AttentionTaskConflict): service.complete_practice()


def test_old_practice_generation_cannot_complete_new_practice(monkeypatch):
    monkeypatch.setattr(session_manager, '_active_id', 742)
    service = AttentionTaskService(); service.pair_display()
    old = service.prepare_practice(task_key='target_tap', age_profile='child', difficulty='easy')
    service.prepare_practice(task_key='go_no_go', age_profile='teen', difficulty='hard')
    with pytest.raises(AttentionTaskConflict, match='Practice changed'):
        service.complete_practice(old['practice_generation'])
    assert service.public_status()['phase'] == 'practice'


def test_old_practice_cannot_cancel_replacement(monkeypatch):
    monkeypatch.setattr(session_manager, '_active_id', 748)
    service = AttentionTaskService(); service.pair_display()
    previous = service.prepare_practice(task_key='target_tap', age_profile='child', difficulty='easy')
    service.prepare_practice(task_key='go_no_go', age_profile='adult', difficulty='standard')
    with pytest.raises(AttentionTaskConflict, match='Practice changed'):
        service.cancel_practice(previous['practice_generation'])
    assert service.public_status()['phase'] == 'practice'


def test_pairing_is_preserved_during_practice_and_invalid_after_session_change(monkeypatch):
    monkeypatch.setattr(session_manager, '_active_id', 743)
    service = AttentionTaskService(); token = service.pair_display()['token']
    service.prepare_practice(task_key='target_tap', age_profile='child', difficulty='easy')
    assert service.pair_display()['token'] == token
    assert service.public_status()['phase'] == 'practice'
    monkeypatch.setattr(session_manager, '_active_id', 744)
    assert not service.validate_display_token(token)


def test_qr_validation_does_not_mark_participant_connected(monkeypatch):
    monkeypatch.setattr(session_manager, '_active_id', 745)
    service = AttentionTaskService()
    token = service.pair_display()['token']
    assert service.validate_display_token(token, mark_seen=False)
    assert service._last_display_seen == 0


def test_changed_participant_requires_new_pairing_before_practice(monkeypatch):
    monkeypatch.setattr(session_manager, '_active_id', 746)
    service = AttentionTaskService()
    service.pair_display()
    monkeypatch.setattr(session_manager, '_active_id', 747)
    with pytest.raises(AttentionTaskConflict, match='Pair the display again'):
        service.prepare_practice(task_key='target_tap', age_profile='child', difficulty='easy')


def test_partial_room_setup_can_be_saved_as_draft():
    with TestClient(app) as client:
        response = client.post('/api/calibration/profiles', json={
            'name': 'Incomplete draft', 'manual_checks': {'lighting': True}})
        assert response.status_code == 201
        assert response.json()['status'] != 'accepted'


@pytest.mark.parametrize('module,name', [(body_module,'body_analysis_service'),(face_module,'face_analysis_service')])
def test_stale_camera_does_not_report_tracking(module, name, monkeypatch):
    monkeypatch.setattr(module, 'settings', replace(module.settings, app_mode='real'))
    manager = getattr(module.camera_system, 'body' if name.startswith('body') else 'face')
    monkeypatch.setattr(manager, 'status_payload', lambda: {'status':'CONNECTED','frame_age_seconds':9})
    service = getattr(module, name)
    monkeypatch.setattr(service.state, 'tracking', True)
    result = service.snapshot()
    assert not result['tracking'] and result['status'] == 'CAMERA OFFLINE'


@pytest.mark.parametrize('method,path', [
    ('GET','/api/sessions/active'),('GET','/api/attention/status'),
    ('GET','/api/participant-display/info'),('POST','/api/attention/abort'),
    ('POST','/api/attention/trials/next'),('GET','/api/research-tasks/status'),
    ('POST','/api/research-tasks/abort'),('POST','/api/research-tasks/trials/next'),
])
def test_other_operator_cannot_access_active_task(method, path):
    suffix = uuid4().hex[:8]
    def account(label):
        return repository.create_user_account(full_name=label+suffix, organization=None,
            professional_title=None, role='operator', token_hash=token_hash(label+suffix),
            token_hint='TEST', expires_at=None)
    first, second = account('first'), account('second')
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, issue_token(Identity(first.id, first.full_name, first.role)))
        participant = client.post('/api/participants', json={'participant_code':'QA_'+suffix}).json()
        started = client.post('/api/sessions/start', json={'participant_id':participant['id']})
        assert started.status_code == 201
        session_id = started.json()['id']
        try:
            client.cookies.set(COOKIE_NAME, issue_token(Identity(second.id, second.full_name, second.role)))
            assert client.request(method, path).status_code == 403
        finally:
            client.cookies.set(COOKIE_NAME, issue_token(Identity(first.id, first.full_name, first.role)))
            client.post(f'/api/sessions/{session_id}/stop')


def test_completed_run_remains_completed_after_session_stop():
    with TestClient(app) as client:
        participant = client.post('/api/participants', json={'participant_code':'QA_DONE_'+uuid4().hex[:8]}).json()
        session = client.post('/api/sessions/start', json={'participant_id':participant['id']}).json()
        attention_task_service.pair_display()
        started = client.post('/api/attention/start', json={'task_key':'go_no_go','age_profile':'adult','difficulty':'easy'})
        assert started.status_code == 200
        attention_task_service._total_trials = 1
        trial = client.post('/api/attention/trials/next').json()
        assert client.post(f"/api/attention/trials/{trial['id']}/complete",json={'responded':False}).status_code == 200
        client.post(f"/api/sessions/{session['id']}/stop")
        report = client.get(f"/api/reports/{session['id']}").json()
        assert report['attention_configuration'][0]['status'] == 'completed'
