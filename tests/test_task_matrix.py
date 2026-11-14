"""API end-to-end task matrix, isolated by conftest; no physical-accuracy claim."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tasks.attention_task import TASK_CATALOG, AGE_PROFILES, DIFFICULTIES


@pytest.mark.parametrize('task', list(TASK_CATALOG))
@pytest.mark.parametrize('age', list(AGE_PROFILES))
@pytest.mark.parametrize('level', list(DIFFICULTIES))
def test_practice_record_report_matrix(task, age, level):
    with TestClient(app) as client:
        participant = client.post('/api/participants', json={
            'participant_code': 'MATRIX_' + uuid4().hex[:10]}).json()
        started = client.post('/api/sessions/start', json={'participant_id': participant['id']})
        assert started.status_code == 201
        session_id = started.json()['id']
        try:
            pairing = client.get('/api/participant-display/info').json()
            from urllib.parse import urlparse, parse_qs
            token = parse_qs(urlparse(pairing['url']).query)['token'][0]
            mode = 'any' if level == 'easy' else 'target_color'
            config = {'task_key': task, 'age_profile': age, 'difficulty': level,
                      'required_pops': 5, 'game_mode': mode, 'target_color': 'sky'}
            practice = client.post('/api/attention/practice', json=config)
            assert practice.status_code == 200
            generation = practice.json()['practice_generation']
            assert client.post('/api/participant-task/practice-complete', params={
                'token': token, 'generation': generation}).status_code == 200
            recorded = client.post('/api/attention/start', json=config)
            assert recorded.status_code == 200
            while client.get('/api/participant-task/status', params={'token': token}).json()['phase'] != 'complete':
                trial_response = client.post('/api/participant-task/trials/next', params={'token': token})
                assert trial_response.status_code == 200
                trial = trial_response.json()
                target = trial['is_target']
                response = client.post(f"/api/participant-task/trials/{trial['id']}/complete",
                    params={'token': token}, json={'responded': target,
                        'reaction_time_ms': 100 if target else None})
                assert response.status_code == 200
            assert client.get('/api/participant-task/status', params={'token': token}).json()['phase'] == 'complete'
        finally:
            client.post(f'/api/sessions/{session_id}/stop')
        report = client.get(f'/api/reports/{session_id}')
        assert report.status_code == 200
        run = report.json()['attention_configuration'][0]
        assert run['status'] == 'completed'
        assert (run['task_key'], run['age_profile'], run['difficulty']) == (task, age, level)
        assert report.json()['participant']['code'] == participant['participant_code']
        assert report.json()['attention']['accuracy'] == 100
        assert report.json()['attention']['correct_pops'] == 5
        exported = client.get(f'/api/exports/sessions/{session_id}.json')
        assert exported.status_code == 200
        assert exported.json()['participant']['code'] == participant['participant_code']
