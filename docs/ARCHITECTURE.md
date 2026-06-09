# Architecture: Educational Ledger Simulator

> **Document scope:** This document explains how the demo models ledger
> concepts. It documents production concerns separately; it does not claim the
> simulator is production payment infrastructure.

---

## 1. Append-Only Ledger Rows

The simulator treats transactions and entries as posted ledger history. Once a
transaction is committed, corrections happen through compensating reversal
transactions instead of destructive edits.

Database safeguards:

| Table | Constraint | Effect |
|-------|------------|--------|
| `entries` | `transaction_id` uses `ondelete="RESTRICT"` | Prevents deleting a transaction while entries reference it |
| `entries` | `account_id` uses `ondelete="RESTRICT"` | Prevents deleting an account while entries reference it |
| `entries` | `amount > 0` check | Keeps sign semantics in `direction`, not in the amount |

The `Transaction.entries` and `Transaction.fx_quote_snapshot` relationships do
not use delete-orphan cascades. The `/api/reset` endpoint and
`bootstrap_database()` recreate the demo schema, but ordinary ledger correction
uses append-only reversals.

---

## 2. Accounting Convention

The project uses asset-normal demo balances:

```text
DEBIT  = increase account balance
CREDIT = decrease account balance
```

Balances are derived from entries:

```sql
SUM(CASE
    WHEN direction = 'DEBIT'  THEN amount
    WHEN direction = 'CREDIT' THEN -amount
END)
```

There is no stored account balance column.

---

## 3. Currency-Aware Invariants

The ledger must balance independently by currency. A globally net-zero sum is
not sufficient because it could hide a USD imbalance behind an opposite EUR
imbalance.

`LedgerEngine.verify_system_invariants()` groups by `Account.currency` through
`entries -> accounts`:

```sql
SELECT a.currency,
       SUM(CASE WHEN e.direction = 'DEBIT' THEN e.amount
                WHEN e.direction = 'CREDIT' THEN -e.amount END) AS net
FROM entries e
JOIN accounts a ON a.id = e.account_id
GROUP BY a.currency
```

Every returned `net` must be zero. Transaction execution also verifies the
newly-created transaction by currency before commit.

Bootstrap uses currency-specific equity accounts:

- `System Equity (USD)`
- `System Equity (EUR)`

The old `MULTI` equity account is intentionally not used because it would allow
currencies to net against each other.

---

## 4. Cross-Currency FX Clearing

For a USD to EUR payment, the simulator creates four legs:

```text
sender                 CREDIT  send_amount_usd
FX_CLEARING_USD        DEBIT   send_amount_usd

FX_CLEARING_EUR        CREDIT  receive_amount_eur
recipient              DEBIT   receive_amount_eur
```

Per-currency totals:

```text
USD: sender credit == FX USD debit
EUR: FX EUR credit == recipient debit
```

The receiver-currency clearing account is checked for sufficient liquidity
before entries are posted.

---

## 5. FX Rate Snapshots and Rounding

The ledger accepts a caller-supplied rate snapshot. It does not fetch live rates.

Core conversion steps:

1. Parse `fx_rate` from a string or `Decimal`; reject Python `float`.
2. Convert source minor units to a Decimal major-unit amount.
3. Multiply by the rate.
4. Quantize to the destination currency precision using `ROUND_HALF_UP`.
5. Post the destination amount as integer minor units.

The `fx_quote_snapshots` table records:

- `transaction_id`
- `from_currency`
- `to_currency`
- `rate`
- `provider` and `quote_id` placeholders
- `timestamp`
- `rounding_mode`
- `source_amount_minor`
- `destination_amount_minor`

This makes demo FX conversion deterministic and auditable without pretending to
be a market-rate or quote-management system.

---

## 6. Idempotency

`transactions.idempotency_key` is unique at the database layer. The ledger also
stores a normalized request fingerprint for payment transactions.

Behavior:

- Same key and same fingerprint returns the original transaction.
- Same key and different fingerprint raises `IdempotencyConflictError`.
- A database `IntegrityError` on the unique idempotency constraint is recovered
  into the same retry/conflict behavior when possible.

This demonstrates the pattern. A real distributed system would also need a
durable idempotency service or database design, request expiry policy, replay
rules, retries, and operational observability.

---

## 7. Reversals

`reverse_transaction()` loads the original entries and creates a new transaction
with flipped directions. It sets:

- `transaction_type = REVERSAL`
- `reversed_transaction_id = <original transaction id>`
- `idempotency_key = REV-<original key>`

The original transaction is not mutated. The dashboard also recognizes reversal
transactions by their `REV-` idempotency key for display compatibility.

---

## 8. Concurrency Demo

The engine exposes a `locking_strategy` parameter:

- `PESSIMISTIC`: uses SQLite `BEGIN IMMEDIATE` for demo writer serialization and
  fetches `Account` rows with `with_for_update=True` for dialects that support
  row locks.
- `OCC`: uses SQLAlchemy `version_id` on `Account` and a version-touch workaround
  so appending entries can still detect conflicting account writes.

These choices are useful for observing race-condition behavior in a simulator.
They are not a complete design for production payment safety. A production
system would need explicit transaction isolation choices, database-specific lock
semantics, retry/backoff policy, reconciliation, monitoring, alerting, and
operational runbooks.

---

## 9. Module Architecture

```text
lightspark-payment-service/
├── src/
│   ├── models.py          # ORM models and enums
│   ├── ledger.py          # LedgerEngine, bootstrap, invariants, display
│   └── api.py             # FastAPI endpoints and request parsing
├── static/                # Vanilla dashboard
├── docs/
│   ├── ARCHITECTURE.md    # This document
│   ├── DESIGN.md          # Design document index
│   ├── engineering-design/
│   │   └── DESIGN.md      # Ledger behavior, limitations, and roadmap
│   └── product-design/
│       └── DESIGN.md      # Dashboard UX, UI, and copy guidance
├── tests/                 # Pytest coverage for ledger/API/frontend
└── pyproject.toml         # Poetry dependency management
```

| Layer | Module | Responsibility |
|-------|--------|----------------|
| State | `src/models.py` | Accounts, transactions, entries, FX quote snapshots |
| Behavior | `src/ledger.py` | Payment execution, invariant checks, idempotency, reversals |
| API | `src/api.py` | REST endpoints, request parsing, error mapping |
| Dashboard | `static/` | Interactive learning UI and race simulation |
