from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import os
import uuid
from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from .models import (
    DATABASE_URL,
    Account,
    AccountType,
)
from .ledger import (
    ConcurrencyConflictError,
    DuplicateTransactionError,
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FASTAPI APP SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app = FastAPI(title="Ledger Engine API")

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

@app.on_event("startup")
def startup_event():
    ensure_bootstrapped()

# Mount static files (HTML, CSS, JS)
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


def _is_render_host(request: Request) -> bool:
    host = request.headers.get("host", "").split(":", maxsplit=1)[0].lower()
    return host.endswith(RENDER_HOST_SUFFIX)


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
    <div class="eyebrow"><span class="pulse" aria-hidden="true"></span>API online</div>
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
    send_dollars: float
    fx_rate: float
    idempotency_key: Optional[str] = None
    locking_strategy: Optional[str] = "PESSIMISTIC"

class ResetResponse(BaseModel):
    status: str
    message: str

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/state")
def get_state():
    """Return the complete ledger state required for the UI."""
    ensure_bootstrapped()
    
    with SessionLocal() as sf:
        # 1. Check Invariant
        net = int(sf.execute(text(
            "SELECT COALESCE(SUM(CASE WHEN direction='DEBIT' THEN amount "
            "WHEN direction='CREDIT' THEN -amount END), 0) FROM entries"
        )).scalar())
        
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
            SELECT t.id, t.timestamp, t.idempotency_key, t.description, COUNT(e.id) as legs
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
                "legs": row[4]
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
            "balanced": net == 0
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
    
    send_cents = round(req.send_dollars * 100)
    idem_key = req.idempotency_key or f"PAY-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    
    if req.sender_id == req.receiver_id:
        raise HTTPException(status_code=400, detail="Sender and Receiver must differ")
        
    try:
        txn = ledger.execute_cross_currency_payment(
            sender_id=req.sender_id,
            receiver_id=req.receiver_id,
            send_amount=send_cents,
            fx_rate=req.fx_rate,
            idempotency_key=idem_key,
            fx_clearing_usd_id=ids["fx_usd"],
            fx_clearing_eur_id=ids["fx_eur"],
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
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=f"Overdraft Prevention: {str(e)}")
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=409, detail=f"Concurrency Conflict (OCC): {str(e)}")
    except Exception as e:
        logging.exception("Payment execution failed")
        raise HTTPException(status_code=500, detail=str(e))


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
