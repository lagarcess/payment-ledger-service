from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_backend_settings_explain_default_origin():
    html = (ROOT / "static" / "index.html").read_text()

    assert 'id="api-default-helper"' in html
    assert 'data-i18n="apiDefaultHelper"' in html


def test_github_pages_uses_render_wake_status_and_timeout():
    script = (ROOT / "static" / "script.js").read_text()

    assert "DEFAULT_REMOTE_API_ORIGIN = 'https://ledger-api-oy0a.onrender.com'" in script
    assert "hostname.endsWith('.onrender.com')" in script
    assert "LEGACY_REMOTE_API_ORIGINS" in script
    assert "https://ledger-api.onrender.com" in script
    assert "currentApiOrigin !== normalizeApiOrigin(storedApiOrigin)" in script
    assert "apiStatusWaking" in script
    assert "function shouldUseRemoteWakeStatus()" in script
    assert "STATE_FETCH_TIMEOUT_REMOTE_MS = 90000" in script


def test_github_pages_explains_backend_controls_without_a_banner():
    readme = (ROOT / "README.md").read_text()
    script = (ROOT / "static" / "script.js").read_text()

    assert "### Backend Controls From The Gear Menu" in readme
    assert "`Warm`" in readme
    assert "`Default`" in readme
    assert "`Save`" in readme
    assert "`/health`" in readme
    assert "remoteWakeHintShown" in script
    assert "apiRemoteWakeHintTitle" in script


def test_readme_explains_render_status_page_and_gated_deploys():
    readme = (ROOT / "README.md").read_text()
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "The Render service root is intentionally an API status page" in readme
    assert "https://ledger-api-oy0a.onrender.com/" in readme
    assert "GitHub Actions" in readme
    assert "After CI Checks Pass" in readme
    assert "Deploy Render API" in workflow
    assert "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/deploys" in workflow


def test_frontend_distinguishes_protected_backend_from_offline():
    script = (ROOT / "static" / "script.js").read_text()
    css = (ROOT / "static" / "style.css").read_text()

    assert "function isProtectedBackendError" in script
    assert "apiStatusProtected" in script
    assert "protectedInvariant" in script
    assert "protectedFlow" in script
    assert "setBackendStatus('protected'" in script
    assert "setBackendStatus('protected', copy.label)" not in script
    assert "setBackendStatus(status, copy.label)" not in script
    assert ".backend-status.protected" in css


def test_mobile_toasts_have_bounded_readable_layout():
    css = (ROOT / "static" / "style.css").read_text()

    assert "overflow-wrap: anywhere" in css
    assert "left: 18px" in css
    assert "right: 18px" in css
    assert "width: auto" in css


def test_quick_guide_is_language_aware_and_designed():
    html = (ROOT / "static" / "index.html").read_text()
    script = (ROOT / "static" / "script.js").read_text()
    css = (ROOT / "static" / "style.css").read_text()

    assert 'class="quick-guide"' in html
    assert 'data-i18n="guideTitle"' in html
    assert 'data-i18n="guideConnectTitle"' in html
    assert "guideRaceBody" in script
    assert ".quick-guide" in css
    assert ".guide-card" in css
