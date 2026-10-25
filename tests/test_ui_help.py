"""Execute the shared plain-language formatter without a browser or DOM."""
from pathlib import Path
import subprocess
import shutil
import pytest


def test_shared_error_help_formats_validation_and_recovery():
    executable = shutil.which('node')
    if not executable:
        pytest.skip('Node is required for JavaScript behavior checks')
    script = Path(__file__).resolve().parents[1] / 'static/js/ui-help.js'
    program = """
      require(process.argv[1]);
      const assert = require('node:assert/strict');
      const help = globalThis.MonitorHelp;
      const invalid = help.errorMessage({detail:[{loc:['body','name'],msg:'Field required'}]},422);
      assert.match(invalid,/name: Field required/);
      assert.match(invalid,/Next: Correct/);
      assert.ok(!invalid.includes('[object Object]'));
      assert.match(help.errorMessage({detail:'Expired'},401),/Sign in again/);
      assert.match(help.errorMessage({detail:'Forbidden'},403),/authorized/);
      assert.match(help.errorMessage(null,500),/server terminal/);
      assert.match(help.glossary['Target FPS'],/not the measured/);
      assert.match(help.glossary['Research timing preset'],/not evidence of clinical validation/);
      assert.equal(help.escapeHTML('<img src=x onerror="boom">'), '&lt;img src=x onerror=&quot;boom&quot;&gt;');
    """
    subprocess.run([executable, '-e', program, str(script)], check=True, timeout=10)


def test_checked_requests_recover_from_http_network_and_invalid_json():
    executable = shutil.which('node')
    if not executable:
        pytest.skip('Node is required for JavaScript behavior checks')
    script = Path(__file__).resolve().parents[1] / 'static/js/ui-help.js'
    program = """
      require(process.argv[1]);
      const assert = require('node:assert/strict');
      (async () => {
        const request = globalThis.MonitorHelp.requestJSON;
        for (const status of [401,403,404,409,413,422,429,500,503]) {
          globalThis.fetch = async () => ({ok:false,status,json:async()=>({detail:'Test failure'})});
          await assert.rejects(request('/test'), error => /Test failure/.test(error.message) && /Next:/.test(error.message));
        }
        let writes=0;
        globalThis.fetch = async () => {writes++;throw new TypeError('offline')};
        await assert.rejects(request('/write',{method:'POST'}),/No automatic write retry/);
        assert.equal(writes,1);
        globalThis.fetch = async () => ({ok:true,status:200,json:async()=>{throw new Error('HTML instead of JSON')}});
        await assert.rejects(request('/test'),/unexpected response/);
        globalThis.fetch = async () => ({ok:true,status:200,json:async()=>({ready:true})});
        assert.deepEqual(await request('/test'),{ready:true});
      })().catch(error => {console.error(error);process.exitCode=1});
    """
    subprocess.run([executable, '-e', program, str(script)], check=True, timeout=10)
