# Enterprise Payment Ledger & Concurrency Simulator

[Open the live GitHub Pages dashboard](https://lagarcess.github.io/payment-ledger-service/)
to try the frontend immediately.

A double-entry payment ledger engine with a Vanilla JS frontend designed to simulate and visualize distributed system edge cases — race conditions, double-spend attacks, and append-only data immutability — in real time.

Built as an interactive testbed for enterprise concurrency patterns, the system exposes two selectable locking strategies (Pessimistic and OCC) through a single API, allowing developers to observe how each mechanism prevents data corruption under simultaneous load.

---

## Key Concepts

This project demonstrates the core fintech and distributed systems principles used by production banking infrastructure. Each concept below explains **why** it matters, **how to see it in action** on the dashboard, and **where the code lives**.

### 1. Double-Entry Invariants

Every transaction in the ledger must be perfectly balanced: **Σ debits == Σ credits**. No account balance is ever updated directly — balances are always derived from the aggregate sum of their entry legs. This fundamental accounting identity guarantees that money is never created or destroyed, only moved between accounts through equal and opposite journal entries. A global system invariant enforces that the net balance of the entire universe of accounts is exactly zero at all times.

- **How to see it at play:** Execute any payment on the dashboard. Switch to the **Ledger Legs** tab to see the individual DEBIT and CREDIT entries that compose the transaction — they will always sum to exactly zero. The green **System Invariant** badge at the top of the main panel continuously verifies that `Σ debits == Σ credits` across the entire ledger. If this badge ever turns red, the system has detected data corruption.
- **Where the code lives:** `src/ledger.py` — the `verify_system_invariants()` method runs the global sum query across all entries. The `_get_account_balance()` helper computes individual account balances from the `DEBIT - CREDIT` aggregate. All four entry legs are created atomically inside `_execute_payment_inner()`.

### 2. Append-Only Immutability & Reversals

Ledger data is structurally immutable at the database engine layer. All foreign keys on the `entries` table use `ondelete="RESTRICT"`, preventing any parent row deletion that would orphan audit history. No SQL `DELETE` or destructive `UPDATE` is ever issued against ledger rows. No `cascade="all, delete-orphan"` exists on any relationship. The **only** way to correct a mistake is to create a **Compensating Transaction** — a new, append-only reversal that flips every DEBIT to CREDIT and vice versa, perfectly zeroing out the original without modifying or removing it.

- **How to see it at play:** Execute a payment, then click the **Reverse** button on that transaction's row in the Journal Entries table. The original transaction receives a strikethrough with a `REVERSED` badge. A brand-new reversal transaction appears below it with a `REVERSAL` badge. Switch to the **Ledger Legs** tab to see the offsetting entries. The System Invariant badge stays green — proving the ledger grew, never shrank. Attempting to reverse the same transaction again will trigger a `409 Already Reversed` rejection.
- **Where the code lives:** `src/models.py` — the `Entry` model's foreign keys enforce `ondelete="RESTRICT"`. `src/ledger.py` — `reverse_transaction()` reads original entries, flips directions, performs a pre-flight overdraft check on USER accounts, and inserts the compensating transaction with a `REV-{original_key}` idempotency guard.

### 3. Concurrency Control (Race Conditions)

The payment engine exposes a **toggleable locking strategy** via a single `locking_strategy` parameter. **Pessimistic Locking** acquires a write lock (`BEGIN IMMEDIATE` on SQLite, `SELECT ... FOR UPDATE` on PostgreSQL) before reading balances, forcing Thread B to block until Thread A commits and then read the updated zero balance — resulting in an `Insufficient Funds` rejection. **Optimistic Concurrency Control (OCC)** loads Account rows without locks and instead bumps the `version_id` via `flag_modified()` at commit time. If a concurrent transaction already incremented the version, SQLAlchemy raises `StaleDataError`, which the engine wraps as a `409 Concurrency Conflict`. Both strategies guarantee that a double-spend attack against the same balance results in exactly one successful commit and one deterministic rejection.

- **How to see it at play:** Select a **Concurrency Strategy** from the dropdown in the sidebar (Pessimistic or OCC). Click **Simulate Concurrency Race**. The system automatically reads the sender's entire balance and fires two simultaneous drain requests via `Promise.all()` at the exact same millisecond. A detailed race results panel will appear showing Thread A and Thread B side-by-side — one committed, one rejected — with the exact error message explaining *why* the lock prevented the double-spend.
- **Where the code lives:** `src/ledger.py` — `_execute_payment_inner()` branches on `locking_strategy`: the `PESSIMISTIC` path executes `BEGIN IMMEDIATE` followed by `session.query(Account).with_for_update().get()`; the `OCC` path calls `session.get(Account, id)` without locks, then `flag_modified(sender_acct, "name")` to force a `version_id` bump. `StaleDataError` is caught in `execute_cross_currency_payment()` and re-raised as `ConcurrencyConflictError`. `static/script.js` — `simulateDoubleSpend()` orchestrates the `Promise.all()` race.

### 4. Cross-Currency FX Clearing

Payments between users with different currencies are never exchanged directly. They route through internal **Corporate FX Clearing** accounts that act as treasury market makers. The sender's currency flows into the corresponding clearing pool, and the receiver's currency flows out of the opposite pool. This four-leg settlement path absorbs currency conversion risk and isolates liquidity management from end-user accounts.

```
Sender (USD) ──CREDIT──▶ FX Clearing (USD) ──DEBIT──▶ FX Clearing (EUR) ──CREDIT──▶ Receiver (EUR)
```

- **How to see it at play:** Select a USD sender and EUR receiver on the dashboard. The **Payment Flow** diagram updates in real time to show the four-leg routing path through both clearing accounts, with the FX-converted amounts. After executing the payment, the FX Clearing rows in the **Accounts** table (highlighted with a subtle tint) will show the updated pool balances. The **Ledger Legs** tab displays all four entry legs with their currency denominations.
- **Where the code lives:** `src/ledger.py` — the four entry legs are created inside `_execute_payment_inner()`, with FX conversion calculated as `recv_amount = round(send_amount * fx_rate)` using strict integer arithmetic. `static/script.js` — `updateFormState()` dynamically renders the flow diagram based on the selected sender/receiver currencies.

### 5. High-Precision Integer Arithmetic

Floating-point numbers are catastrophically imprecise for financial calculations — a rounding error of even a fraction of a cent compounds across billions of transactions. All monetary amounts in this system are stored and calculated as **64-bit `BigInteger`** values representing minor currency units (cents for USD/EUR, msats for Lightning). The decimal point exists exclusively in the frontend presentation layer. `$100.00` is processed as `10000` end-to-end.

- **How to see it at play:** The backend API returns all amounts as raw integers (e.g., `balance_cents: 10000`). The frontend reformats these to localized currency strings (`$100.00`) only at render time. You can verify this by inspecting any `/api/state` response — every monetary field is an integer.
- **Where the code lives:** `src/models.py` — the `Entry.amount` column uses `BigInteger` with `CheckConstraint("amount > 0")`. `src/ledger.py` — all arithmetic operates on Python `int` values; no `float` or `Decimal` is used in any calculation path. `static/script.js` — the `formatCurrency()` helper divides by 100 for display.

### 6. Idempotency & Safe Resets

Idempotency prevents duplicate transactions from network retries or double-clicks. Every payment request requires a unique, single-use `idempotency_key` enforced by a database-level unique constraint. The system also provides a deterministic environment reset that drops all tables and reconstructs the ledger from an identical seed state — enabling repeatable edge-case testing without manual cleanup.

- **How to see it at play:** Uncheck **Auto-generate key** in the sidebar. Type a custom idempotency key and execute a payment. Attempt the exact same payment again with the same key — the system will reject it with a `409 Idempotency Rejection` toast showing the original transaction ID. To restore the environment to its pristine seed state, click **Reset Database**. All accounts, transactions, and entries are destroyed and recreated from the same genesis block.
- **Where the code lives:** `src/models.py` — `Transaction.idempotency_key` has a `unique=True` constraint. `src/ledger.py` — `_execute_payment_inner()` checks for existing keys before proceeding. `src/api.py` — the `/api/reset` endpoint calls `bootstrap_database()`, which drops all tables and reseeds through append-only equity journal entries.

---

## Repository Structure

```
├── src/
│   ├── __init__.py          # Package marker
│   ├── models.py            # State Layer — ORM models, enums, DB constants
│   ├── ledger.py            # Behavior Layer — LedgerEngine, locking, reversals
│   └── api.py               # API Layer — FastAPI endpoints, request models
├── static/
│   ├── index.html           # Dashboard markup
│   ├── script.js            # Frontend logic, i18n, race simulator
│   └── style.css            # Design system tokens, component styles
├── docs/
│   ├── ARCHITECTURE.md      # Enterprise compliance mechanisms
│   └── DESIGN.md            # UI/UX design guidelines and token system
├── AGENTS.md                # Agent instructions and strict prohibitions
├── pyproject.toml            # Poetry dependency manifest
└── README.md
```

### Layer Separation

| Layer | File | Responsibility |
|-------|------|---------------|
| **State** | `src/models.py` | SQLAlchemy ORM definitions (`Account`, `Transaction`, `Entry`), enumerations, database path constants, `version_id` OCC column |
| **Behavior** | `src/ledger.py` | `LedgerEngine` class, payment execution, locking strategies, reversal logic, invariant verification, database bootstrap |
| **API** | `src/api.py` | FastAPI server, request validation, endpoint routing, error mapping to HTTP status codes |
| **Testbed** | `static/` | Interactive dashboard with race simulation, reversal UI, real-time invariant monitoring, i18n (EN/ES) |

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/) for dependency management

### Install

```bash
git clone https://github.com/lagarcess/payment-ledger-service.git
cd payment-ledger-service
poetry install
```

### Bootstrap the Database

Seeds the ledger with initial accounts, treasury capitalisation, and FX clearing liquidity via append-only equity journal entries:

```bash
poetry run python -m src.ledger
```

### Launch the Server

```bash
poetry run uvicorn src.api:app --reload
```

Open ```http://127.0.0.1:8000/``` to access the dashboard.

### GitHub Pages Frontend

The vanilla dashboard in `static/` is also publishable as a GitHub Pages project
site. The included workflow deploys that folder on pushes to `master`:

```text
https://lagarcess.github.io/payment-ledger-service/
```

On localhost, the frontend defaults API calls to `http://127.0.0.1:8000`. On
GitHub Pages, it defaults to the Render backend origin:

```text
https://ledger-api.onrender.com
```

Open the gear menu to inspect or override the API URL. The panel shows the
resolved default backend for the current host. On GitHub Pages, the first
`/api/state` request automatically wakes the Render backend with a longer
cold-start timeout; the **Warm** control calls `/health` as a manual retry. You
can also open the Pages frontend with an explicit backend override:

```text
https://lagarcess.github.io/payment-ledger-service/?api=https://ledger-api.onrender.com
```

### Backend Controls From The Gear Menu

On the GitHub Pages dashboard, open the gear icon in the top-right corner and
use the **Backend** section to connect the static UI to a running API:

| Control | What it does |
|---------|--------------|
| `API URL` | Backend origin used by the dashboard, such as `https://ledger-api.onrender.com` or `http://127.0.0.1:8000`. Do not include `/api/state`; the frontend adds API paths automatically. |
| `Save` | Stores the API URL in browser local storage so refreshes keep using the same backend. |
| `Default` | Restores the automatic default: localhost during local development, Render on GitHub Pages. |
| `Warm` | Calls `{API URL}/health` to wake or check the backend, then refreshes ledger state. This is useful for Render free-tier cold starts. |

The Pages experience stays intentionally quiet: if the default Render backend is
cold, the dashboard automatically starts waking it with the first `/api/state`
request and briefly shows a toast instead of adding a permanent banner.
If the configured API returns `401` or `403`, the gear menu reports a protected
or wrong backend URL instead of treating it as an ordinary offline cold start.

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
| `GET` | `/api/state` | Returns the complete ledger state: invariant status, metrics, account balances, transactions, and entry legs |
| `POST` | `/api/payment` | Executes a cross-currency payment. Accepts `sender_id`, `receiver_id`, `send_dollars`, `fx_rate`, `idempotency_key`, and `locking_strategy` (`PESSIMISTIC` or `OCC`) |
| `POST` | `/api/reverse/{id}` | Creates a compensating reversal transaction. Returns `404` if not found, `409` if already reversed, `400` if reversal would overdraft |
| `POST` | `/api/reset` | Drops all tables and reseeds the database to its initial state |

### Error Semantics

| HTTP Status | Meaning |
|-------------|---------|
| `400` | Overdraft prevention — insufficient funds in sender or FX clearing account |
| `404` | Transaction not found (reversal target does not exist) |
| `409` | Idempotency rejection (duplicate key), already reversed, or OCC version conflict |
| `500` | Unhandled server error |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.10+, FastAPI, SQLAlchemy, SQLite |
| Frontend | HTML5, Vanilla JavaScript, CSS |
| Dependencies | Poetry (`pyproject.toml`) |
| Fonts | Inter, Inter Tight (Google Fonts) |
