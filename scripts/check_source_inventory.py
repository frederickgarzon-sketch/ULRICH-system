"""Verify Git-tracked local imports without importing AI/server dependencies."""
import ast
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def missing_imports(tracked):
    tracked = set(tracked)
    missing = set()
    for name in tracked:
        if not name.endswith(".py") or not name.startswith(("app/", "analysis/", "rpi_node/")):
            continue
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8-sig"), filename=name)
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): modules.extend(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules.append(node.module)
        for module in modules:
            if module.split('.')[0] not in {"app", "analysis", "rpi_node"}: continue
            path = module.replace('.', '/')
            if path + '.py' not in tracked and path + '/__init__.py' not in tracked:
                missing.add((name, module))
    return sorted(missing)


if __name__ == '__main__':
    files = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    missing = missing_imports(files)
    for source, module in missing: print(f'MISSING TRACKED MODULE: {module} (imported by {source})')
    if missing: raise SystemExit(1)
    print('Tracked source import inventory passed (not a runtime dependency test).')
