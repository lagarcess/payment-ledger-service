# Architecture: Enterprise Compliance Mechanisms

> **Document scope**: This document details the four enterprise-grade compliance mechanisms enforced by the Lightspark Payment Service ledger engine.  For UI/UX design guidelines, see [`DESIGN.md`](./DESIGN.md).

---

## 1. Append-Only Immutability

The ledger enforces **strict append-only semantics** at both the application and database levels.  Once a transaction or entry is committed, it is permanent and cannot be modified or deleted.

### Database-Level Enforcement

| Table          | Foreign Key Constraint          | Effect                                                                 |
|----------------|---------------------------------|------------------------------------------------------------------------|
| `entries`      | `ondelete="RESTRICT"` → `transactions` | Prevents deletion of any `Transaction` row while entries reference it. |
| `entries`      | `ondelete="RESTRICT"` → `accounts`     | Prevents deletion of any `Account` row while entries reference it.     |

### Application-Level Enforcement

- **No cascade delete**: The `Transaction.entries` relationship uses `cascade="save-update, merge"` — explicitly excluding `delete` and `delete-orphan`.  SQLAlchemy will **never** cascade a deletion from a parent to its child entries.
- **Append-only bootstrap**: The `bootstrap_database()` function seeds the ledger exclusively through balanced `INSERT` operations against a System Equity account.  No `DELETE` or destructive `UPDATE` statements are issued against ledger rows.  The only DDL operations are `DROP ALL` / `CREATE ALL` for schema recreation.

### Correction Mechanism

Errors are corrected through **reversal entries** (new append-only journal entries that cancel the effect of the original), never through row deletion or in-place modification.

---

## 2. Double-Entry Balance Invariant (Σ debits == Σ credits)

Every `Transaction` in the ledger must satisfy the fundamental accounting identity:

```
Σ DEBIT amounts  ==  Σ CREDIT amounts  (globally, and per transaction)
```

### Central FX Clearing Constraint

Cross-currency payments route through **Corporate FX Clearing Accounts** using a 4-leg balanced entry structure:

```
┌──────────┐       Leg 1 (USD)        ┌─────────────────────┐
│  User A  │ ──── CREDIT ──────────▶  │  FX Clearing (USD)  │
│  (USD)   │                DEBIT ◀── │                     │
└──────────┘                          └─────────────────────┘
                                                │
                                      Leg 2 (EUR)│
                                                ▼
┌──────────┐                          ┌─────────────────────┐
│  User B  │ ◀──── DEBIT  ────────── │  FX Clearing (EUR)  │
│  (EUR)   │                CREDIT ──▶│                     │
└──────────┘                          └─────────────────────┘
```

### Invariant Verification

The `LedgerEngine.verify_system_invariants()` method asserts that the global net balance across all entries is exactly zero:

```sql
SELECT COALESCE(SUM(
    CASE WHEN direction = 'DEBIT'  THEN amount
         WHEN direction = 'CREDIT' THEN -amount
    END
), 0) AS net
FROM entries
```

If `net ≠ 0`, an `InvariantViolationError` is raised, indicating data corruption.

### Overdraft Protection

`LedgerEngine.verify_no_negative_user_balances()` ensures no `USER` account carries a negative computed balance.  Corporate/clearing accounts are excluded as they may legitimately carry negative positions.

---

## 3. Pessimistic Row Locking

The `execute_cross_currency_payment()` method acquires **`FOR UPDATE`** locks on the `Account` rows *before* computing aggregate balances.  This prevents concurrent double-spends under high concurrency.

### Locking Strategy

```python
# Step 1: Lock Account rows (prevents concurrent reads)
session.query(Account).with_for_update().get(sender_id)
session.query(Account).with_for_update().get(fx_clearing_eur_id)

# Step 2: Compute balances AFTER locks are held
sender_balance = self._get_account_balance(session, sender_id)
fx_eur_balance = self._get_account_balance(session, fx_clearing_eur_id)
```

### Why Lock the Row, Not the Aggregate?

The `_get_account_balance()` function computes a `SUM()` aggregate over the `entries` table.  Applying `FOR UPDATE` to an aggregate query is syntactically invalid in most SQL dialects (including PostgreSQL).  Instead, we lock the **parent Account row** first, which:

1. Establishes an exclusive row-level lock on the account.
2. Blocks any concurrent transaction that also attempts to lock the same account.
3. Guarantees that the subsequent balance aggregate reads a consistent snapshot.

### Optimistic Concurrency Control (OCC)

As an additional safety layer, the `Account` model carries a `version_id` column configured as SQLAlchemy's version counter (`__mapper_args__ = {"version_id_col": version_id}`).  Any concurrent modification to the same account row will raise `StaleDataError`.

---

## 4. 64-Bit Minor Unit Integer Arithmetic

All monetary values are stored and computed as **integers representing the smallest currency unit** (e.g., cents for USD/EUR).

### Database Enforcement

| Column          | Type          | Constraint                                        |
|-----------------|---------------|---------------------------------------------------|
| `entries.amount`| `BigInteger`  | 64-bit signed integer; supports values up to ≈ $92 quadrillion |
| —               | —             | `CheckConstraint("amount > 0")` — amounts are always positive  |

### Design Rationale

- **No IEEE-754 rounding errors**: Floating-point numbers (`float`, `double`) introduce microscopic rounding errors during arithmetic.  In a financial ledger, even a fraction-of-a-cent error compounds over millions of transactions.
- **Sign carried by direction**: The `direction` column (`DEBIT` / `CREDIT`) carries the semantic sign.  The `amount` column is always a positive integer, enforced by a database-level `CHECK` constraint.
- **Display-only formatting**: The decimal point is reintroduced at the presentation layer (frontend JavaScript) for human readability.  The backend never divides by 100 for computation — only for display formatting via `_fmt_amount()`.

### Capacity

`BigInteger` (64-bit signed) supports values up to `9,223,372,036,854,775,807` — equivalent to approximately **$92.2 quadrillion** in cents.  This exceeds the total global money supply by several orders of magnitude.

---

## Module Architecture

```
lightspark-payment-service/
├── src/
│   ├── models.py          # State Layer — ORM models, enums, DB constants
│   ├── ledger.py           # Behavior Layer — LedgerEngine, bootstrap, display
│   └── api.py              # API Layer — FastAPI endpoints
├── static/                 # Frontend — HTML, CSS, JS
├── docs/
│   ├── ARCHITECTURE.md     # This document
│   └── DESIGN.md           # UI/UX design guidelines
├── AGENTS.md               # AI agent operational rules
├── README.md               # Project overview
└── pyproject.toml           # Poetry dependency management
```

| Layer    | Module         | Responsibility                                              |
|----------|----------------|-------------------------------------------------------------|
| State    | `src/models.py`| ORM models, enums, DB path, declarative base                |
| Behavior | `src/ledger.py`| Transaction execution, invariant checks, bootstrap, display |
| API      | `src/api.py`   | FastAPI REST endpoints, request/response models              |
