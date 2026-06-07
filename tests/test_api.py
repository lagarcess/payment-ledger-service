from src.api import app


def test_health_check_reports_ok():
    health_route = next(
        route for route in app.routes if getattr(route, "path", None) == "/health"
    )

    assert "GET" in health_route.methods
    assert health_route.endpoint() == {"status": "ok"}
