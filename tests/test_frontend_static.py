from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_backend_settings_explain_default_origin():
    html = (ROOT / "static" / "index.html").read_text()

    assert 'id="api-default-helper"' in html
    assert 'data-i18n="apiDefaultHelper"' in html


def test_github_pages_uses_render_wake_status_and_timeout():
    script = (ROOT / "static" / "script.js").read_text()

    assert "apiStatusWaking" in script
    assert "function shouldUseRemoteWakeStatus()" in script
    assert "STATE_FETCH_TIMEOUT_REMOTE_MS = 90000" in script
