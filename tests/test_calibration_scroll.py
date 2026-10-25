from pathlib import Path


def test_calibration_uses_document_scroll_without_legacy_compact_layout():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates/calibration.html').read_text(encoding='utf-8')
    css = (root / 'static/css/calibration-v2.css').read_text(encoding='utf-8')
    assert 'calibration-compact.css' not in template
    assert 'calibration-v2.css?v=20261003-scroll' in template
    assert 'html{overflow-y:auto!important}' in css


def test_calibration_streams_only_current_step_previews():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates/calibration.html').read_text(encoding='utf-8')
    script = (root / 'static/js/calibration.js').read_text(encoding='utf-8')
    assert ' src="/preview/' not in template
    assert 'data-preview-src="/preview/face"' in template
    assert "image.removeAttribute('src')" in script
    assert "classList.contains('active')" in script
