# Educational Multi-Currency Ledger Simulator

[Open the live GitHub Pages dashboard](https://lagarcess.github.io/payment-ledger-service/)
to try the frontend immediately.

This project is an educational multi-currency ledger simulator. It demonstrates double-entry accounting, FX clearing, idempotency, reversals, and concurrency tradeoffs, but it is not production payment infrastructure.

The app is a portfolio/learning project built with FastAPI, SQLAlchemy, SQLite,
and a vanilla HTML/CSS/JavaScript dashboard. It is useful for exploring ledger
concepts and failure modes, not for holding money or making operational payment
guarantees.

---

## What It Demonstrates

### Double-Entry Accounting

Balances are derived from immutable entry legs. The project uses this sign
convention:

- `DEBIT` increases an account balance.
- `CREDIT` decreases an account balance.

Every posted transaction must balance by currency. A USD debit must be matched
by USD credit, and an EUR debit must be matched by EUR credit. The simulator no
longer uses a `MULTI` equity account that lets different currencies net against
each other.

### Cross-Currency FX Clearing

For a USD to EUR payment, funds route through currency-specific clearing
accounts:

```text
sender                 CREDIT  send_amount_usd
FX_CLEARING_USD        DEBIT   send_amount_usd

FX_CLEARING_EUR        CREDIT  receive_amount_eur
recipient              DEBIT   receive_amount_eur
```

The USD side and EUR side each balance independently.

### FX Rates and Rounding

The ledger accepts an FX rate snapshot from the caller. It does not fetch live
rates. Core conversion uses `Decimal` with explicit `ROUND_HALF_UP` rounding,
then posts integer minor-unit amounts to the ledger. The transaction records the
rate, source amount, destination amount, currencies, timestamp, and rounding
mode in an `fx_quote_snapshots` row.

### Idempotency

Every payment has a database-unique `idempotency_key`. A retry with the same key
and same normalized request fingerprint returns the original transaction. A
retry with the same key but different payment details raises an idempotency
conflict.

### Reversals

Corrections use compensating reversal transactions. The simulator appends new
entry legs with flipped directions instead of mutating or deleting original
ledger rows.

### Concurrency Tradeoffs

The dashboard can switch between a pessimistic SQLite demo path and an
optimistic version-counter path. These are teaching mechanisms for race
conditions, not a complete distributed concurrency design. SQLite
`BEGIN IMMEDIATE` serializes writers for the demo; production systems would need
database-specific isolation choices, retries, reconciliation, monitoring, and
operational controls.

---

## Repository Structure

```text
├── src/
│   ├── __init__.py          # Package marker
│   ├── models.py            # ORM models and enums
│   ├── ledger.py            # LedgerEngine, invariants, payments, reversals
│   └── api.py               # FastAPI endpoints
├── static/
│   ├── index.html           # Dashboard markup
│   ├── script.js            # Frontend logic and i18n
│   └── style.css            # Dashboard styles
├── docs/
│   ├── ARCHITECTURE.md      # Accounting and architecture notes
│   ├── DESIGN.md            # Design document index
│   ├── engineering-design/
│   │   └── DESIGN.md        # Ledger behavior, limits, and roadmap
│   └── product-design/
│       └── DESIGN.md        # Dashboard UX, UI, and copy guidance
├── tests/
│   ├── test_ledger.py       # Accounting, FX, idempotency, concurrency tests
│   ├── test_api.py          # API boundary tests
│   └── test_frontend_static.py
├── AGENTS.md                # Agent instructions and ledger safety rules
├── pyproject.toml           # Poetry dependency manifest
└── README.md
```

### Layer Separation

| Layer | File | Responsibility |
|-------|------|----------------|
| State | `src/models.py` | SQLAlchemy models for accounts, transactions, entries, and FX snapshots |
| Behavior | `src/ledger.py` | Payment execution, invariant checks, idempotency, reversals, bootstrap |
| API | `src/api.py` | FastAPI routing, request parsing, error mapping |
| Dashboard | `static/` | Interactive demo UI, race simulation, transaction reversal controls |

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/)

### Install

```bash
git clone https://github.com/lagarcess/payment-ledger-service.git
cd payment-ledger-service
poetry install
```

### Bootstrap the Database

Seeds the ledger with user balances, FX clearing liquidity, and
currency-specific equity accounts:

```bash
poetry run python -m src.ledger
```

### Launch the Server

```bash
poetry run uvicorn src.api:app --reload
```

Open `http://127.0.0.1:8000/` to access the dashboard.

### Run Tests

```bash
poetry run pytest
poetry run ruff check
```

---

## GitHub Pages Frontend

The vanilla dashboard in `static/` is publishable as a GitHub Pages project
site:

```text
https://lagarcess.github.io/payment-ledger-service/
```

On localhost, the frontend defaults API calls to `http://127.0.0.1:8000`. On
GitHub Pages, it defaults to the Render backend origin:

```text
https://ledger-api-oy0a.onrender.com
```

Open the gear menu to inspect or override the API URL. The panel shows the
resolved default backend for the current host. On GitHub Pages, the first
`/api/state` request automatically wakes the Render backend with a longer
cold-start timeout; the **Warm** control calls `/health` as a manual retry.

You can also open the Pages frontend with an explicit backend override:

```text
https://lagarcess.github.io/payment-ledger-service/?api=https://ledger-api-oy0a.onrender.com
```

The Render service root is intentionally an API status page instead of a second
dashboard:

```text
https://ledger-api-oy0a.onrender.com/
```

Use it when you want to confirm the backend is online. It links directly to the
GitHub Pages dashboard, `/health`, `/api/state`, and the FastAPI docs.

### Backend Controls From The Gear Menu

| Control | What it does |
|---------|--------------|
| `API URL` | Backend origin used by the dashboard, such as `https://ledger-api-oy0a.onrender.com` or `http://127.0.0.1:8000`. Do not include `/api/state`; the frontend adds API paths automatically. |
| `Save` | Stores the API URL in browser local storage so refreshes keep using the same backend. |
| `Default` | Restores the automatic default: localhost during local development, Render on GitHub Pages. |
| `Warm` | Calls `{API URL}/health` to wake or check the backend, then refreshes ledger state. |

The Pages experience stays intentionally quiet: if the default Render backend is
cold, the dashboard starts waking it with the first `/api/state` request and
briefly shows a toast instead of adding a permanent banner. If the configured
API returns `401` or `403`, the gear menu reports a protected or wrong backend
URL instead of treating it as an ordinary offline cold start.

### Deployment Flow

GitHub Pages publishes the static dashboard from `static/`. Render hosts the
FastAPI backend. Render native auto-deploy is kept off in `render.yaml` because
the repository CI is the deployment gate: `.github/workflows/ci.yml` runs
metadata validation, Ruff, and pytest, then triggers the Render API deploy only
after those checks pass on `master`.

The workflow expects a repository secret named `RENDER_API_KEY` with permission
to deploy service `srv-d8il3du47okc739gbja0`. If you manage the service
directly from Render instead of GitHub Actions, use **After CI Checks Pass**
rather than **On Commit** so failed ledger or concurrency tests cannot redeploy
the demo API.

### CORS Configuration

The API allows local development origins and `https://lagarcess.github.io` by
default. Add extra frontend origins at deploy time with a comma-separated
environment variable:

```bash
CORS_ALLOW_ORIGINS=https://example.com,http://localhost:5173
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/state` | Returns invariant status, metrics, account balances, transactions, and entry legs |
| `GET` | `/api/transactions/{id}` | Returns one transaction, its entries, idempotency key, reversal pointer, and FX snapshot if present |
| `POST` | `/api/payment` | Executes a payment. Prefer `send_amount_minor: int` and `fx_rate: string`; `send_amount: string` is accepted at the API boundary |
| `POST` | `/api/reverse/{id}` | Creates a compensating reversal transaction |
| `POST` | `/api/reset` | Drops and recreates the demo database seed state |

### Payment Request Example

```json
{
  "sender_id": 1,
  "receiver_id": 2,
  "send_amount_minor": 5000,
  "fx_rate": "0.92",
  "idempotency_key": "PAY-DEMO-001",
  "locking_strategy": "PESSIMISTIC"
}
```

### Error Semantics

| HTTP Status | Meaning |
|-------------|---------|
| `400` | Invalid amount, unsupported route, insufficient funds, or reversal overdraft |
| `404` | Transaction not found |
| `409` | Idempotency conflict, already reversed, or OCC version conflict |
| `500` | Unexpected server error |

---

## Known Limitations

- SQLite is used for demonstration, not as a durable payment database.
- Accounts are single-currency; true multi-currency account balances would need
  currency on each entry or a separate balance dimension.
- FX rates are caller-supplied snapshots; there is no live provider integration.
- Fees are documented as a future extension and are not posted by the current
  API.
- There is no distributed idempotency store, reconciliation pipeline,
  monitoring, alerting, authentication, authorization, or migration strategy.
- The concurrency controls demonstrate tradeoffs but are not a complete design
  for real payment infrastructure.

See [`docs/engineering-design/DESIGN.md`](docs/engineering-design/DESIGN.md)
for the detailed ledger design notes and “more time” roadmap. See
[`docs/product-design/DESIGN.md`](docs/product-design/DESIGN.md) for
dashboard UX, UI, and copy guidance.
