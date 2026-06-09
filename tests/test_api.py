import pytest
from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from src.api import (
    PaymentRequest,
    SessionLocal,
    _request_amount_minor,
    app,
    app_state,
    execute_payment,
    get_transaction,
    read_root,
    reset_database,
    reverse_transaction,
)
from src.models import Account, AccountType


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


def test_payment_request_prefers_integer_minor_units():
    req = PaymentRequest(
        sender_id=1,
        receiver_id=2,
        send_amount_minor=1234,
        send_amount="99.99",
        fx_rate="0.92",
    )

    assert _request_amount_minor(req) == 1234


def test_payment_request_parses_decimal_amount_at_api_boundary():
    req = PaymentRequest(
        sender_id=1,
        receiver_id=2,
        send_amount="12.345",
        fx_rate="0.92",
    )

    assert _request_amount_minor(req) == 1235


def test_payment_endpoint_rejects_invalid_locking_strategy():
    app_state.clear()
    reset_database()

    req = PaymentRequest(
        sender_id=1,
        receiver_id=2,
        send_amount_minor=1000,
        fx_rate="0.92",
        idempotency_key="API-BAD-LOCK",
        locking_strategy="TYPO",
    )

    with pytest.raises(HTTPException) as exc:
        execute_payment(req)

    assert exc.value.status_code == 400
    assert "locking_strategy" in exc.value.detail


def test_same_currency_api_payment_does_not_require_fx_rate():
    app_state.clear()
    reset_database()

    with SessionLocal() as session:
        with session.begin():
            charlie = Account(
                name="Charlie (User 3)",
                currency="USD",
                type=AccountType.USER,
            )
            session.add(charlie)
            session.flush()
            charlie_id = charlie.id

    req = PaymentRequest(
        sender_id=1,
        receiver_id=charlie_id,
        send_amount_minor=1000,
        idempotency_key="API-SAME-CURRENCY-NO-FX",
        locking_strategy="PESSIMISTIC",
    )
    response = execute_payment(req)

    assert response["status"] == "success"


def test_transaction_audit_marks_original_reversal_status():
    app_state.clear()
    reset_database()

    payment = execute_payment(PaymentRequest(
        sender_id=1,
        receiver_id=2,
        send_amount_minor=1000,
        fx_rate="0.92",
        idempotency_key="API-REVERSAL-AUDIT",
        locking_strategy="PESSIMISTIC",
    ))
    original_id = payment["transaction_id"]

    reversal = reverse_transaction(original_id)
    audit = get_transaction(original_id)

    assert audit["is_reversed"] is True
    assert audit["reversal_transaction_id"] == reversal["transaction_id"]


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
    assert "API is online" in body
    assert "https://lagarcess.github.io/payment-ledger-service/" in body
    assert 'href="/health"' in body
    assert 'href="/api/state"' in body


def test_render_runtime_env_shows_api_status_page(monkeypatch):
    monkeypatch.setenv("RENDER", "true")

    response = read_root(_request_for_host("internal-render-host"))
    body = response.body.decode()

    assert isinstance(response, HTMLResponse)
    assert "Ledger API" in body
    assert "Open Dashboard" in body


def test_local_root_still_serves_dashboard():
    response = read_root(_request_for_host("127.0.0.1:8000"))

    assert isinstance(response, FileResponse)
    assert response.status_code == 200
    assert response.path.endswith("static/index.html")
