# Enterprise Payment Ledger & Concurrency Simulator

A production-grade, double-entry payment ledger engine with a Vanilla JS frontend designed to simulate and visualize distributed system edge cases — race conditions, double-spend attacks, and append-only data immutability — in real time.

Built as an interactive testbed for enterprise concurrency patterns, the system exposes two selectable locking strategies (Pessimistic and OCC) through a single API, allowing developers to observe how each mechanism prevents data corruption under simultaneous load.

---

## Core Architectural Concepts

### Double-Entry Invariants

Every monetary movement in the system is recorded as a balanced pair of journal entries. No account balance is ever updated directly — balances are always derived from the aggregate sum of their entry legs.

Cross-currency transfers route through internal **Corporate FX Clearing** accounts. A payment from USD to EUR produces four atomic entry legs:

```
CREDIT  Sender (USD)           →  Funds leave the sender
DEBIT   FX Clearing (USD)      →  USD pool absorbs the funds
CREDIT  FX Clearing (EUR)      →  EUR pool releases converted funds
DEBIT   Receiver (EUR)         →  Funds arrive at the receiver
```

The system enforces a global invariant at all times: **Σ debits == Σ credits == 0**. A non-zero result indicates data corruption and is treated as a critical failure.

### Append-Only Immutability

Ledger data is structurally immutable at the database engine layer:

- All foreign keys on the `entries` table use `ondelete="RESTRICT"`, preventing any parent row deletion that would orphan audit history.
- No `DELETE` or destructive `UPDATE` statement is ever issued against the `entries` or `transactions` tables.
- No `cascade="all, delete-orphan"` configuration exists on any ledger relationship.

**Correcting mistakes** is handled exclusively through **Compensating Transactions** (reversals). A reversal reads the original transaction, flips every DEBIT to CREDIT and vice versa, and inserts them as a new, append-only transaction. The original record is never modified or removed.

### Concurrency Control

The payment engine exposes a **toggleable locking strategy** via a single `locking_strategy` parameter:

| Strategy | Mechanism | Failure Mode |
|----------|-----------|-------------|
| **Pessimistic** | `BEGIN IMMEDIATE` (SQLite) / `SELECT ... FOR UPDATE` (PostgreSQL) acquires a write lock before reading balances | Thread B **blocks** until Thread A commits, then reads the updated (zero) balance → `400 Insufficient Funds` |
| **OCC** | Account rows loaded without locks; `version_id` bumped via `flag_modified()` at commit time | Thread B's version check fails at flush → `StaleDataError` → `409 Concurrency Conflict` |

Both strategies guarantee that a double-spend attack against the same account balance results in exactly one successful commit and one deterministic rejection.

### High-Precision Integer Arithmetic

All monetary amounts are stored as **64-bit `BigInteger`** values representing minor currency units (cents, msats). No `float`, `Decimal`, or `Numeric` type is used at any layer:

- **Database**: `BigInteger` column with `CheckConstraint("amount > 0")`
- **Python**: Native `int` — all FX conversion uses `round(send_amount * fx_rate)`
- **Frontend**: Integer-to-display conversion occurs exclusively in the presentation layer

This eliminates floating-point drift across billions of transactions and supports sub-cent precision for Lightning Network micropayments.

---

## The Visual Testbed

The frontend is a Vanilla HTML/JS/CSS dashboard that transforms abstract concurrency theory into observable behavior.

### Race Condition Simulator

The **Simulate Concurrency Race** button programmatically reads the sender's full account balance and fires two simultaneous drain-entire-balance requests using `Promise.all()`:

```javascript
const [resA, resB] = await Promise.all([
    fetch(`/api/payment`, { method: 'POST', body: JSON.stringify(payloadA) }),
    fetch(`/api/payment`, { method: 'POST', body: JSON.stringify(payloadB) })
]);
```

Both requests hit the API at the exact same millisecond. The **Concurrency Strategy** dropdown determines which locking mechanism the backend uses to resolve the conflict. The UI renders the result of both threads side-by-side, showing which committed and which was rejected — and why.

### Transaction Reversal Flow

Each non-seed transaction row in the Journal Entries table includes a **Reverse** action button. Clicking it triggers a `POST /api/reverse/{id}` call that:

1. Reads the original transaction's entry legs
2. Creates a new transaction with every direction flipped (DEBIT ↔ CREDIT)
3. Inserts it as an append-only compensating record

The original transaction receives a `REVERSED` badge and strikethrough styling. The new reversal transaction appears with a `REVERSAL` badge. The system invariant remains perfectly balanced throughout.

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

Open **http://127.0.0.1:8000/** to access the dashboard.

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
