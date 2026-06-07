from fastapi.middleware.cors import CORSMiddleware

from src.api import app


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
