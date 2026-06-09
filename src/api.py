from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional
import os
import uuid
from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, StrictInt
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from .models import (
    DATABASE_URL,
    Account,
    AccountType,
    Entry,
    FxQuoteSnapshot,
    Transaction,
)
from .ledger import (
    ConcurrencyConflictError,
    DuplicateTransactionError,
    IdempotencyConflictError,
    InsufficientFundsError,
    LedgerEngine,
    TransactionNotFoundError,
    bootstrap_database,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATABASE SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def _set_pragmas(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ledger = LedgerEngine(SessionLocal)

# Global state for bootstrapped IDs
app_state: Dict[str, Any] = {}

def ensure_bootstrapped():
    if "account_ids" not in app_state:
        app_state["account_ids"] = bootstrap_database(engine, SessionLocal)
        app_state["pay_n"] = 0

@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_bootstrapped()
    yield


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FASTAPI APP SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app = FastAPI(title="Ledger Engine API", lifespan=lifespan)

GITHUB_PAGES_DASHBOARD_URL = "https://lagarcess.github.io/payment-ledger-service/"
RENDER_HOST_SUFFIX = ".onrender.com"

DEFAULT_CORS_ALLOW_ORIGINS = (
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "https://lagarcess.github.io",
)


def get_cors_allow_origins() -> list[str]:
    configured_origins = [
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys((*DEFAULT_CORS_ALLOW_ORIGINS, *configured_origins)))


# Enable CORS for local development and the GitHub Pages static dashboard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allow_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (HTML, CSS, JS)
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


def _is_render_host(request: Request) -> bool:
    if os.getenv("RENDER", "").lower() == "true":
        return True

    host = request.headers.get("host", "").split(":", maxsplit=1)[0].lower()
    external_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").lower()
    return host.endswith(RENDER_HOST_SUFFIX) or host == external_hostname


def _render_api_status_page(request: Request) -> HTMLResponse:
    api_origin = escape(str(request.base_url).rstrip("/"))
    dashboard_url = escape(GITHUB_PAGES_DASHBOARD_URL)
    return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>Ledger API Status</title>
  <style>
    :root {{
      color-scheme: light dark;
      --ink: #191c1f;
      --body: #3a3d40;
      --canvas: #ffffff;
      --soft: #f4f4f4;
      --hairline: #e2e2e7;
      --dark: #000000;
      --primary: #494fdf;
      --teal: #00a87e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      min-height: 100vh;
      margin: 0;
      display: grid;
      place-items: center;
      padding: 32px;
      background:
        linear-gradient(180deg, rgba(73, 79, 223, 0.08), transparent 34%),
        var(--canvas);
      color: var(--ink);
      font-family:
        Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }}
    main {{
      width: min(100%, 720px);
      border: 1px solid var(--hairline);
      border-radius: 20px;
      padding: clamp(28px, 6vw, 48px);
      background: rgba(255, 255, 255, 0.88);
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 22px;
      color: var(--body);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    .pulse {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--teal);
      box-shadow: 0 0 0 6px rgba(0, 168, 126, 0.12);
    }}
    h1 {{
      max-width: 12ch;
      margin: 0;
      font-size: clamp(42px, 9vw, 78px);
      line-height: 1;
      font-weight: 600;
      letter-spacing: 0;
    }}
    p {{
      max-width: 56ch;
      margin: 20px 0 0;
      color: var(--body);
      font-size: 17px;
      line-height: 1.55;
    }}
    code {{
      display: inline-block;
      max-width: 100%;
      margin-top: 24px;
      padding: 10px 12px;
      overflow-wrap: anywhere;
      border: 1px solid var(--hairline);
      border-radius: 12px;
      background: var(--soft);
      color: var(--ink);
      font-size: 13px;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 30px;
    }}
    a {{
      min-height: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 11px 18px;
      border-radius: 999px;
      border: 1px solid var(--hairline);
      color: var(--ink);
      font-size: 14px;
      font-weight: 700;
      text-decoration: none;
    }}
    a.primary {{
      border-color: var(--dark);
      background: var(--dark);
      color: #ffffff;
    }}
    a:focus-visible {{
      outline: 3px solid rgba(73, 79, 223, 0.35);
      outline-offset: 3px;
    }}
    @media (prefers-color-scheme: dark) {{
      body {{
        background:
          linear-gradient(180deg, rgba(73, 79, 223, 0.22), transparent 38%),
          #000000;
        color: #ffffff;
      }}
      main {{
        border-color: rgba(255, 255, 255, 0.12);
        background: #16181a;
      }}
      p, .eyebrow {{ color: rgba(255, 255, 255, 0.72); }}
      code {{
        border-color: rgba(255, 255, 255, 0.12);
        background: #0a0a0a;
        color: #ffffff;
      }}
      a {{
        border-color: rgba(255, 255, 255, 0.34);
        color: #ffffff;
      }}
      a.primary {{
        border-color: #ffffff;
        background: #ffffff;
        color: #000000;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow"><span class="pulse" aria-hidden="true"></span>API is online</div>
    <h1>Ledger API</h1>
    <p>
      This Render service hosts the FastAPI backend for the payment ledger demo.
      Use GitHub Pages for the dashboard, or inspect the API directly below.
    </p>
    <code>{api_origin}</code>
    <nav aria-label="Service links">
      <a class="primary" href="{dashboard_url}">Open Dashboard</a>
      <a href="/health">Health</a>
      <a href="/api/state">State</a>
      <a href="/docs">API Docs</a>
    </nav>
  </main>
</body>
</html>""")


@app.get("/")
def read_root(request: Request):
    if _is_render_host(request):
        return _render_api_status_page(request)
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


@app.get("/style.css", include_in_schema=False)
@app.head("/style.css", include_in_schema=False)
def read_style_css():
    return FileResponse(os.path.join(_STATIC_DIR, "style.css"), media_type="text/css")


@app.get("/script.js", include_in_schema=False)
@app.head("/script.js", include_in_schema=False)
def read_script_js():
    return FileResponse(
        os.path.join(_STATIC_DIR, "script.js"),
        media_type="application/javascript",
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PaymentRequest(BaseModel):
    sender_id: int
    receiver_id: int
    send_amount_minor: Optional[StrictInt] = None
    send_amount: Optional[str] = None
    fx_rate: Optional[str] = None
    idempotency_key: Optional[str] = None
    locking_strategy: Optional[str] = "PESSIMISTIC"

class ResetResponse(BaseModel):
    status: str
    message: str


def _parse_decimal_amount_to_minor(raw_amount: str) -> int:
    try:
        amount = Decimal(str(raw_amount).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise HTTPException(status_code=400, detail="Amount must be a decimal string.") from exc

    if not amount.is_finite() or amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive.")

    rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(rounded.scaleb(2).to_integral_exact())


def _request_amount_minor(req: PaymentRequest) -> int:
    if req.send_amount_minor is not None:
        if req.send_amount_minor <= 0:
            raise HTTPException(status_code=400, detail="send_amount_minor must be positive.")
        return req.send_amount_minor

    if req.send_amount is None:
        raise HTTPException(
            status_code=400,
            detail="Provide send_amount_minor or send_amount.",
        )
    return _parse_decimal_amount_to_minor(req.send_amount)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/state")
def get_state():
    """Return the complete ledger state required for the UI."""
    ensure_bootstrapped()
    
    with SessionLocal() as sf:
        # 1. Check currency-aware invariant
        per_currency = ledger.get_currency_invariant_balances()
        transaction_imbalances = ledger.get_transaction_currency_imbalances()
        imbalances = {
            currency: net
            for currency, net in per_currency.items()
            if net != 0
        }
        net = (
            sum(abs(value) for value in imbalances.values())
            + sum(abs(row["net"]) for row in transaction_imbalances)
        )
        
        # 2. Get Totals
        r = sf.execute(text(
            "SELECT COALESCE(SUM(CASE WHEN direction='DEBIT' THEN amount END), 0), "
            "COALESCE(SUM(CASE WHEN direction='CREDIT' THEN amount END), 0) FROM entries"
        )).fetchone()
        total_debits, total_credits = int(r[0]), int(r[1])
        
        # 3. Get User Accounts (for the dropdowns)
        user_accounts = []
        accounts = sf.query(Account).filter(Account.type == AccountType.USER).order_by(Account.id).all()
        for a in accounts:
            balance = ledger.get_account_balance(a.id)
            user_accounts.append({
                "id": a.id,
                "name": a.name,
                "currency": a.currency,
                "balance_cents": balance,
                "balance_display": f"{balance / 100:,.2f}"
            })
            
        # 4. Get Data Table Data (Accounts)
        acct_rows = sf.execute(text("""
            SELECT a.id, a.name, a.type, a.currency,
                   COALESCE(SUM(CASE WHEN e.direction='DEBIT' THEN e.amount
                                     WHEN e.direction='CREDIT' THEN -e.amount END), 0) as bal
            FROM accounts a
            LEFT JOIN entries e ON e.account_id = a.id
            GROUP BY a.id ORDER BY a.id
        """)).fetchall()
        
        accounts_table = []
        for row in acct_rows:
            accounts_table.append({
                "id": row[0],
                "name": row[1],
                "type": str(row[2]).replace("AccountType.", ""),
                "currency": row[3],
                "balance_display": f"{row[4] / 100:,.2f}"
            })
            
        # 5. Get Data Table Data (Transactions)
        txn_rows = sf.execute(text("""
            SELECT t.id, t.timestamp, t.idempotency_key, t.description,
                   t.transaction_type, t.reversed_transaction_id, COUNT(e.id) as legs
            FROM transactions t
            LEFT JOIN entries e ON e.transaction_id = t.id
            GROUP BY t.id ORDER BY t.id
        """)).fetchall()
        
        txns_table = []
        user_txn_count = 0
        for row in txn_rows:
            if not str(row[2]).startswith("SEED"):
                user_txn_count += 1
            txns_table.append({
                "id": row[0],
                "timestamp": row[1],
                "idempotency_key": row[2],
                "description": row[3],
                "transaction_type": str(row[4]).replace("TransactionType.", ""),
                "reversed_transaction_id": row[5],
                "legs": row[6]
            })
            
        # 6. Get Data Table Data (Entries)
        entry_rows = sf.execute(text("""
            SELECT e.id, e.transaction_id, a.name, a.type, a.currency, e.direction, e.amount
            FROM entries e
            JOIN accounts a ON a.id = e.account_id
            ORDER BY e.transaction_id, e.id
        """)).fetchall()
        
        entries_table = []
        for row in entry_rows:
            entries_table.append({
                "id": row[0],
                "txn_id": row[1],
                "account_name": row[2],
                "account_type": str(row[3]).replace("AccountType.", ""),
                "currency": row[4],
                "direction": str(row[5]).replace("EntryDirection.", ""),
                "amount_display": f"{row[6] / 100:,.2f}"
            })

    return {
        "invariant": {
            "net": net,
            "balanced": not imbalances and not transaction_imbalances,
            "per_currency": per_currency,
            "imbalances": imbalances,
            "transaction_imbalances": transaction_imbalances,
        },
        "metrics": {
            "total_debits_cents": total_debits,
            "total_credits_cents": total_credits,
            "transaction_count": len(txns_table),
            "user_transaction_count": user_txn_count,
            "entry_count": len(entries_table),
            "account_count": len(accounts_table)
        },
        "user_accounts": user_accounts,
        "tables": {
            "accounts": accounts_table,
            "transactions": txns_table,
            "entries": entries_table
        },
        "session": {
            "pay_n": app_state.get("pay_n", 0)
        }
    }


@app.post("/api/payment")
def execute_payment(req: PaymentRequest):
    ensure_bootstrapped()
    ids = app_state["account_ids"]
    
    send_cents = _request_amount_minor(req)
    idem_key = req.idempotency_key or f"PAY-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    
    if req.sender_id == req.receiver_id:
        raise HTTPException(status_code=400, detail="Sender and Receiver must differ")
        
    try:
        with SessionLocal() as session:
            sender = session.get(Account, req.sender_id)
            receiver = session.get(Account, req.receiver_id)

        if sender is not None and receiver is not None and sender.currency == receiver.currency:
            txn = ledger.execute_same_currency_payment(
                sender_id=req.sender_id,
                receiver_id=req.receiver_id,
                send_amount=send_cents,
                idempotency_key=idem_key,
                locking_strategy=req.locking_strategy or "PESSIMISTIC",
            )
        else:
            if req.fx_rate is None:
                raise HTTPException(
                    status_code=400,
                    detail="fx_rate is required for cross-currency payments.",
                )
            sender_fx_id = ids.get(f"fx_{sender.currency.lower()}") if sender else ids["fx_usd"]
            receiver_fx_id = ids.get(f"fx_{receiver.currency.lower()}") if receiver else ids["fx_eur"]
            if sender_fx_id is None or receiver_fx_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="No FX clearing account is configured for this currency route.",
                )

            txn = ledger.execute_cross_currency_payment(
                sender_id=req.sender_id,
                receiver_id=req.receiver_id,
                send_amount=send_cents,
                fx_rate=req.fx_rate,
                idempotency_key=idem_key,
                fx_clearing_usd_id=sender_fx_id,
                fx_clearing_eur_id=receiver_fx_id,
                locking_strategy=req.locking_strategy or "PESSIMISTIC",
            )
        
        app_state["pay_n"] = app_state.get("pay_n", 0) + 1
        return {
            "status": "success",
            "transaction_id": txn.id,
            "idempotency_key": idem_key,
            "locking_strategy": req.locking_strategy or "PESSIMISTIC",
            "message": f"Transaction #{txn.id} committed successfully."
        }
        
    except DuplicateTransactionError as e:
        raise HTTPException(status_code=409, detail=f"Idempotency Rejection: {str(e)}")
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=409, detail=f"Idempotency Conflict: {str(e)}")
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=f"Overdraft Prevention: {str(e)}")
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=409, detail=f"Concurrency Conflict (OCC): {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Payment execution failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transactions/{transaction_id}")
def get_transaction(transaction_id: int):
    """Return an auditable transaction view with entries and FX snapshot."""
    ensure_bootstrapped()

    with SessionLocal() as session:
        txn = session.get(Transaction, transaction_id)
        if txn is None:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        entries = (
            session.query(Entry)
            .join(Account)
            .filter(Entry.transaction_id == transaction_id)
            .order_by(Entry.id)
            .all()
        )
        fx_snapshot = (
            session.query(FxQuoteSnapshot)
            .filter(FxQuoteSnapshot.transaction_id == transaction_id)
            .first()
        )
        reversal = (
            session.query(Transaction)
            .filter(Transaction.reversed_transaction_id == transaction_id)
            .first()
        )

        return {
            "id": txn.id,
            "timestamp": txn.timestamp,
            "description": txn.description,
            "idempotency_key": txn.idempotency_key,
            "transaction_type": txn.transaction_type.value,
            "request_fingerprint": txn.request_fingerprint,
            "reversed_transaction_id": txn.reversed_transaction_id,
            "is_reversed": reversal is not None,
            "reversal_transaction_id": reversal.id if reversal is not None else None,
            "entries": [
                {
                    "id": entry.id,
                    "account_id": entry.account_id,
                    "account_name": entry.account.name,
                    "currency": entry.account.currency,
                    "direction": entry.direction.value,
                    "amount_minor": entry.amount,
                }
                for entry in entries
            ],
            "fx_quote_snapshot": None if fx_snapshot is None else {
                "from_currency": fx_snapshot.from_currency,
                "to_currency": fx_snapshot.to_currency,
                "rate": fx_snapshot.rate,
                "provider": fx_snapshot.provider,
                "quote_id": fx_snapshot.quote_id,
                "timestamp": fx_snapshot.timestamp,
                "rounding_mode": fx_snapshot.rounding_mode,
                "source_amount_minor": fx_snapshot.source_amount_minor,
                "destination_amount_minor": fx_snapshot.destination_amount_minor,
            },
        }


@app.post("/api/reverse/{transaction_id}")
def reverse_transaction(transaction_id: int):
    """Create a compensating reversal for an existing transaction."""
    ensure_bootstrapped()
    
    try:
        rev_txn = ledger.reverse_transaction(transaction_id)
        return {
            "status": "success",
            "transaction_id": rev_txn.id,
            "original_transaction_id": transaction_id,
            "message": f"Reversal transaction #{rev_txn.id} committed. "
                       f"Original transaction #{transaction_id} has been offset."
        }
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateTransactionError as e:
        raise HTTPException(status_code=409, detail=f"Already Reversed: {str(e)}")
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=f"Reversal Overdraft: {str(e)}")
    except Exception as e:
        logging.exception("Reversal failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset", response_model=ResetResponse)
def reset_database():
    app_state["account_ids"] = bootstrap_database(engine, SessionLocal)
    app_state["pay_n"] = 0
    return {"status": "success", "message": "Database reset to seed state."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
