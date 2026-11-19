import subprocess
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_session_source_is_not_ignored():
    result = subprocess.run(['git', 'check-ignore', '--no-index', 'app/sessions/session_manager.py'],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1, result.stdout


def test_tracked_local_imports_are_complete():
    spec = importlib.util.spec_from_file_location('inventory', ROOT / 'scripts/check_source_inventory.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    assert 'app/sessions/session_manager.py' in tracked
    assert not module.missing_imports(tracked)
