# Agent Instructions: Lightspark Payment Service

Welcome! You are operating in the `lightspark-payment-service` codebase. This
is an **educational multi-currency payment ledger simulator**. It demonstrates
double-entry ledger mechanics, FX clearing, idempotency, reversals, and
concurrency tradeoffs, but it is not production payment infrastructure.

## Technology Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Vanilla HTML5, JavaScript, CSS (No JS frameworks)
- **Dependency Management:** Poetry (`pyproject.toml`)
- **Key Files:**
  - `src/models.py`: ORM models (`Account`, `Transaction`, `Entry`, FX snapshots), enumerations, DB constants.
  - `src/ledger.py`: `LedgerEngine`, custom exceptions, append-only bootstrap, invariant checks.
  - `src/api.py`: FastAPI server exposing state, payment execution, transaction audit, reversal, and reset endpoints.
  - `static/`: Frontend assets (`index.html`, `style.css`, `script.js`).
  - `docs/ARCHITECTURE.md`: Accounting and implementation notes.
  - `docs/DESIGN.md`: Index for the separate design documents.
  - `docs/engineering-design/DESIGN.md`: Ledger behavior, design choices, limitations, and extension roadmap.
  - `docs/product-design/DESIGN.md`: Dashboard UX, UI, visual language, and copy guidance.

---

## Strict Ledger Safety Rules

These rules protect the learning value and accounting correctness of the demo.

### 1. Do Not Destructively Modify Posted Ledger Rows

Do not write or execute:

- A SQL `DELETE` statement against the `entries` or `transactions` tables.
- A SQL `UPDATE` statement that modifies `amount`, `direction`, `account_id`, or `transaction_id` columns on the `entries` table.
- A SQL `UPDATE` statement that modifies `idempotency_key`, `description`, or `timestamp` columns on the `transactions` table.
- Any SQLAlchemy `.delete()` call against `Entry` or `Transaction` objects.
- Any `cascade="all, delete-orphan"` configuration on ledger relationships.

Correction mechanism: if a transaction was recorded incorrectly, create a new
reversal transaction with new append-only entries that cancel the effect of the
original.

### 2. Keep Posted Money Amounts as Integer Minor Units

Do not:

- Store posted monetary amounts as `Float`, `Numeric`, `Decimal`, or any non-integer type in the database.
- Perform posted balance arithmetic with Python `float`.
- Remove or weaken the `CheckConstraint("amount > 0")` on the `entries` table.
- Remove or downgrade `BigInteger` on posted amount columns.

The ledger posts money as `BigInteger` at the database level and `int` in Python.
The decimal point exists at API/frontend boundaries and in FX-rate conversion.
`Decimal` is allowed for parsing caller-supplied FX rates and display amounts,
then the result must be quantized into integer minor units before entries are
created. Do not store FX rates as floating-point values; store the supplied rate
snapshot as text metadata.

### 3. Preserve Double-Entry and Currency-Aware Invariants

Do not:

- Create an `Entry` without the corresponding balancing entry legs in the same `Transaction`.
- Create a transaction where `SUM(DEBIT) != SUM(CREDIT)` for any involved currency.
- Let a USD imbalance be hidden by an opposite EUR imbalance.
- Add a `MULTI` account that allows currencies to net against each other.
- Directly update account balances. Balances are derived from immutable entries.

Current sign convention:

- `DEBIT` increases an account balance.
- `CREDIT` decreases an account balance.

Keep this convention unless you deliberately update all code, tests, docs, and
UI copy together.

### 4. Preserve Immutability Guards

Do not:

- Change `ondelete="RESTRICT"` to `"CASCADE"` or `"SET NULL"` on any `Entry` foreign key.
- Add delete cascades to `Transaction`, `Account`, or FX snapshot relationships.
- Remove the `version_id` column from `Account`.

### 5. Keep Concurrency Claims and Code Honest

Do not:

- Remove the `locking_strategy` parameter from payment execution flows.
- Mix concurrency models, such as using the OCC version-touch path inside the pessimistic path.
- Apply `.with_for_update()` to aggregate sum queries. It may only be applied directly to `Account` row fetches.
- Remove the `BEGIN IMMEDIATE` SQLite workaround without replacing the pessimistic demo behavior.

Document SQLite locking as a simulator constraint. It is not equivalent to a
full production row-locking or distributed payment-safety design.

---

## Core Principles

1. **Double-entry accounting:** Every transaction balances per currency.
2. **Integer minor units:** Posted money amounts are integers.
3. **FX clearing:** Cross-currency payments route through currency-specific clearing accounts.
4. **ACID transaction blocks:** Multi-leg operations commit or roll back atomically.
5. **Idempotency:** Unique keys and request fingerprints prevent duplicate posting.
6. **Overdraft protection:** End-user accounts cannot drop below zero.
7. **Append-only corrections:** Use reversals, not destructive edits.
8. **Honest scope:** This is a prototype and learning project, not payment infrastructure.

---

## Development Workflow

### Running the App

Use Poetry:

```bash
poetry run python -m src.ledger
poetry run uvicorn src.api:app --reload
```

The dashboard is available at `http://127.0.0.1:8000/`.

### Modifying the Frontend

- The frontend is in `static/`.
- It uses vanilla HTML/JS/CSS. Do not introduce React, Tailwind, or another framework unless the user explicitly requests it.
- Keep API compatibility with the dashboard. The UI may display decimal dollars, but payment requests should prefer `send_amount_minor` and string `fx_rate`.

### Making Changes

- If you change SQLAlchemy models, recreate the demo database via `/api/reset` or `poetry run python -m src.ledger`.
- Add or update tests for accounting, FX rounding, idempotency, reversals, and API behavior.
- Keep docs clear about known limitations and future production concerns.

---

## Git Commit Instructions

Generate commit messages following Conventional Commits.

Format:

```text
<type>(scope): <short summary>
```

Requirements:

- **Types:** `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `build`, `ci`
- **Scope:** Optional but preferred.
- **Summary:** Imperative mood, max 72 characters, no trailing period.
- **Body:** Only if needed; explain why, not what.
- **Footer:** Use for breaking changes or issue closure.

Suggested message for this refactor:

```text
refactor(ledger): reframe simulator and enforce currency-aware invariants
```

---

## Pull Request Instructions

Use this structure:

```markdown
## Summary
- What does this PR do?
- High-level explanation in 1-3 sentences

## Changes
- Bullet list of key changes
- Group related modifications

## Motivation
- Why was this change needed?
- Link to issues if applicable

## Impact
- User-facing changes
- Performance, security, or DX implications

## Testing
- How was this tested?
- Include edge cases if relevant

## Risks/Rollback
- Potential risks
- How to revert safely

## Checklist
- [ ] Tests added/updated
- [ ] Docs updated (if needed)
- [ ] Backward compatibility considered
```
