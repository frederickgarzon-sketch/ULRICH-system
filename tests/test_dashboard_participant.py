from pathlib import Path
import shutil
import subprocess
import pytest


def test_participant_change_refreshes_gate_without_removed_delete_button():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required')
    source = Path(__file__).resolve().parents[1] / 'static/js/dashboard.js'
    program = r'''
    const assert = require('node:assert/strict');
    const text = require('node:fs').readFileSync(process.argv[1], 'utf8');
    let refreshed = 0, change;
    const select = {addEventListener: (event, handler) => {change=handler;}};
    const byId = id => id === 'participant-select' ? select : null;
    let activeSessionId = null;
    const updateCalibrationGate = async () => {refreshed++;};
    eval(text.split('\n').find(line => line.startsWith('function updateParticipantDeleteButton')));
    eval(text.split('\n').find(line => line.startsWith('byId("participant-select")?.addEventListener')));
    (async()=>{await change({target:{value:'1'}});assert.equal(refreshed,1);})().catch(e=>{console.error(e);process.exitCode=1;});
    '''
    result = subprocess.run([node, '-e', program, str(source)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_late_readiness_response_cannot_disable_active_session_stop():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required')
    source = Path(__file__).resolve().parents[1] / 'static/js/dashboard.js'
    program = r'''
    const assert=require('node:assert/strict');
    const text=require('node:fs').readFileSync(process.argv[1],'utf8');
    const start=text.indexOf('async function updateCalibrationGate(){');
    const end=text.indexOf('function updateParticipantDeleteButton',start);
    const select={value:'1'}, button={disabled:false};
    const byId=id=>id==='participant-select'?select:id==='session-button'?button:null;
    const ensureCalibrationGate=()=>{};
    let activeSessionId=null,calibrationGateRequest=0,resolve;
    const MonitorHelp={requestJSON:()=>new Promise(done=>{resolve=done;})};
    eval(text.slice(start,end));
    (async()=>{const request=updateCalibrationGate();activeSessionId=9;resolve({ready:false});await request;assert.equal(button.disabled,false);})().catch(e=>{console.error(e);process.exitCode=1;});
    '''
    result = subprocess.run([node, '-e', program, str(source)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_shared_styles_preserve_hidden_panels_and_calibration_navigation():
    root = Path(__file__).resolve().parents[1]
    css = (root / 'static/css/ui-help.css').read_text(encoding='utf-8')
    calibration = (root / 'static/js/calibration.js').read_text(encoding='utf-8')
    assert '[hidden]{display:none!important}' in css
    assert 'if(completed||!coachBusy)return' in calibration
