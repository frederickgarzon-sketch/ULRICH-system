"""Role/list/export boundary tests with authentication enabled and isolated data."""
from dataclasses import replace
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app import main
from app.database.database import initialize_database
from app.database.repository import repository
from app.services.access_control import COOKIE_NAME, Identity, issue_token, token_hash


@pytest.mark.parametrize('role', ['owner', 'admin', 'operator', 'reviewer'])
def test_foreign_record_lists_and_exports_are_scoped(monkeypatch, role):
    initialize_database()
    suffix = uuid4().hex
    first = repository.create_user_account(full_name='First '+suffix, organization=None,
        professional_title=None, role='operator', token_hash=token_hash('first'+suffix),
        token_hint='QA', expires_at=None)
    second = repository.create_user_account(full_name='Second '+suffix, organization=None,
        professional_title=None, role=role, token_hash=token_hash('second'+suffix),
        token_hint='QA', expires_at=None)
    monkeypatch.setattr(main, 'settings', replace(main.settings, auth_enabled=True))
    with TestClient(main.app) as client:
        client.cookies.set(COOKIE_NAME, issue_token(Identity(first.id, first.full_name, first.role)))
        participant = client.post('/api/participants', json={'participant_code':'PRIVATE_'+suffix[:10]}).json()
        started = client.post('/api/sessions/start', json={'participant_id':participant['id']})
        assert started.status_code == 201
        session_id = started.json()['id']
        client.post(f'/api/sessions/{session_id}/stop')
        client.cookies.set(COOKIE_NAME, issue_token(Identity(second.id, second.full_name, second.role)))
        privileged = role in {'owner','admin'}
        listed = client.get('/api/participants')
        sessions = client.get('/api/sessions')
        assert listed.status_code == sessions.status_code == 200
        assert (participant['id'] in [item['id'] for item in listed.json()]) == privileged
        assert (session_id in [item['id'] for item in sessions.json()]) == privileged
        for path in [f'/api/sessions/{session_id}', f'/api/reports/{session_id}',
                     f'/api/exports/sessions/{session_id}.json', f'/api/exports/sessions/{session_id}.zip']:
            assert client.get(path).status_code == (200 if privileged else 403)
        assert client.get('/api/users').status_code == (200 if privileged else 403)
        if role == 'reviewer':
            assert client.post('/api/participants', json={'participant_code':'BLOCKED_'+suffix[:10]}).status_code == 403
        client.cookies.clear()
        assert client.get('/api/participants').status_code == 401
        assert client.get('/api/reports/'+str(session_id)).status_code == 401
