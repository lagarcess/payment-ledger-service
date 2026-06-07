from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from src.api import app, read_root


def _request_for_host(host: str, scheme: str = "http") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "root_path": "",
            "scheme": scheme,
            "server": (host.split(":", maxsplit=1)[0], 443 if scheme == "https" else 80),
            "client": ("testclient", 50000),
            "headers": [(b"host", host.encode("ascii"))],
            "query_string": b"",
        }
    )


def test_health_check_reports_ok():
    health_route = next(
        route for route in app.routes if getattr(route, "path", None) == "/health"
    )

    assert "GET" in health_route.methods
    assert health_route.endpoint() == {"status": "ok"}


def test_github_pages_origin_is_allowed_for_api_requests():
    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert "https://lagarcess.github.io" in cors_middleware.kwargs["allow_origins"]
    assert "*" not in cors_middleware.kwargs["allow_origins"]


def test_root_asset_aliases_support_pages_relative_paths():
    route_paths = {getattr(route, "path", None) for route in app.routes}

    assert "/style.css" in route_paths
    assert "/script.js" in route_paths


def test_render_root_shows_api_status_page():
    response = read_root(
        _request_for_host("ledger-api-oy0a.onrender.com", scheme="https")
    )
    body = response.body.decode()

    assert isinstance(response, HTMLResponse)
    assert response.status_code == 200
    assert "Ledger API" in body
    assert "API online" in body
    assert "https://lagarcess.github.io/payment-ledger-service/" in body
    assert 'href="/health"' in body
    assert 'href="/api/state"' in body


def test_local_root_still_serves_dashboard():
    response = read_root(_request_for_host("127.0.0.1:8000"))

    assert isinstance(response, FileResponse)
    assert response.status_code == 200
    assert response.path.endswith("static/index.html")
