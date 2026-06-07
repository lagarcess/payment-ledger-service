# Agent Instructions: Lightspark Payment Service

Welcome! You are operating in the `lightspark-payment-service` codebase. This is a **double-entry payment ledger engine** designed to execute cross-currency transfers with enterprise-grade compliance guarantees.

## Technology Stack
- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Vanilla HTML5, JavaScript, CSS (No JS frameworks)
- **Dependency Management:** Poetry (`pyproject.toml`)
- **Key Files:**
  - `src/models.py`: State Layer — ORM models (`Account`, `Transaction`, `Entry`), enumerations, DB constants.
  - `src/ledger.py`: Behavior Layer — `LedgerEngine` class, custom exceptions, append-only bootstrap, display utilities.
  - `src/api.py`: API Layer — FastAPI server exposing endpoints for state, payment execution, and reset.
  - `static/`: Frontend assets (`index.html`, `style.css`, `script.js`).
  - `docs/ARCHITECTURE.md`: Enterprise compliance mechanisms documentation.
  - `docs/DESIGN.md`: UI/UX design guidelines and token system.

---

## ⛔ STRICT PROHIBITIONS — ABSOLUTE RULES

> **These rules are NON-NEGOTIABLE.  Violation of any rule below constitutes a critical system failure.  There are NO exceptions.**

### 1. NEVER Write SQL `DELETE` or `UPDATE` Against Ledger Tables

You MUST NOT, under any circumstances, write or execute:

- A SQL `DELETE` statement against the `entries` or `transactions` tables.
- A SQL `UPDATE` statement that modifies `amount`, `direction`, `account_id`, or `transaction_id` columns on the `entries` table.
- A SQL `UPDATE` statement that modifies `idempotency_key`, `description`, or `timestamp` columns on the `transactions` table.
- Any SQLAlchemy `.delete()` call against `Entry` or `Transaction` objects.
- Any `cascade="all, delete-orphan"` configuration on ledger relationships.

**Correction mechanism:** If a transaction was recorded incorrectly, the ONLY acceptable fix is to create a **new reversal transaction** with new append-only entries that cancel the effect of the original.

### 2. NEVER Use Floating-Point Numbers for Monetary Amounts

You MUST NOT, under any circumstances:

- Store monetary amounts as `Float`, `Numeric`, `Decimal`, or any non-integer type in the database.
- Perform monetary arithmetic using Python `float` or `Decimal` types.  All monetary math uses Python `int`.
- Remove or weaken the `CheckConstraint("amount > 0")` on the `entries` table.
- Remove or downgrade `BigInteger` to `Integer` on the `amount` column.

**The ONLY acceptable type for monetary amounts is `BigInteger` at the database level and `int` at the Python level.  The decimal point exists exclusively at the presentation layer.**

### 3. NEVER Bypass the Double-Entry Invariant

You MUST NOT:

- Create an `Entry` without a corresponding opposite `Entry` in the same `Transaction`.
- Create a `Transaction` where `Σ DEBIT amounts ≠ Σ CREDIT amounts`.
- Directly update an account balance.  Balances are always computed from the sum of entries.

### 4. NEVER Remove Immutability Guards

You MUST NOT:

- Change `ondelete="RESTRICT"` to `"CASCADE"` or `"SET NULL"` on any Foreign Key in `Entry`.
- Add `cascade="all, delete-orphan"` to any relationship on `Transaction` or `Account`.
- Remove the `version_id` (OCC) column from `Account`.

---

## Core Principles & Invariants

When modifying this codebase, you MUST adhere to the following fintech and accounting principles:

1. **Double-Entry Accounting & System Invariants:** 
   - Every transaction must be perfectly balanced (`Σ debits == Σ credits`). 
   - The global system invariant dictates that the net balance of all accounts combined is exactly zero at all times.
   - Do NOT simply update a balance. Money must move from one account to another using equal and opposite journal entries.
2. **Integer Arithmetic (Minor Units):** 
   - Never use floats for currency. All monetary amounts are stored and calculated as integers (e.g., cents for USD/EUR, where $100.00 is `10000`).
3. **Cross-Currency FX Clearing:** 
   - Payments between different currencies (e.g., USD to EUR) route through internal "Corporate FX Clearing" accounts. Do not directly convert and move money between end-user accounts of different currencies.
4. **ACID Transactions:** 
   - Ledger entry creations are wrapped in strict `with session.begin():` blocks. If any leg fails or overdrafts, the entire operation rolls back.
5. **Idempotency:** 
   - Every request uses a unique `idempotency_key` enforced by a database constraint to prevent duplicate transactions.
6. **Overdraft Protection:** 
   - End-user accounts cannot drop below a zero balance. Always check for sufficient funds and raise an `InsufficientFundsError` if necessary.
7. **Pessimistic Row Locking:**
   - Lock `Account` rows with `.with_for_update()` *before* computing aggregate balances. Never apply `FOR UPDATE` to aggregate queries.
8. **Optimistic Concurrency Control:**
   - `Account.version_id` is auto-incremented on every update. Concurrent modifications raise `StaleDataError`.

---

## Development Workflow

### Running the App
The project uses Poetry. Run commands using `poetry run`.

1. **Seed/Reset the database:**
   ```bash
   poetry run python -m src.ledger
   ```
2. **Start the development server:**
   ```bash
   poetry run uvicorn src.api:app --reload
   ```

The dashboard will be available at `http://127.0.0.1:8000/`.

### Modifying the Frontend
- The frontend is located in the `static/` directory.
- It uses vanilla HTML/JS/CSS. Do not introduce frameworks like React or Tailwind unless explicitly requested by the user.
- The `docs/DESIGN.md` file contains design guidelines and analysis (a sleek dark interface, gradient cards, fintech precision). Consult this file before making UI or aesthetic changes.

### Making Changes
- **Database Schema:** If you change the SQLAlchemy models in `src/models.py`, you may need to recreate the database (the `/api/reset` endpoint or running `src/ledger.py` directly handles dropping and recreating tables).
- **Testing:** Ensure any new transaction types strictly preserve the double-entry principles and the global system invariant of zero.
- **Architecture Reference:** See `docs/ARCHITECTURE.md` for detailed documentation of compliance mechanisms.

---

## Git Commit Instructions

Generate a commit message following **Conventional Commits** specifications.

### Format
```
<type>(scope): <short summary>

[optional body]

[optional footer(s)]
```

### Requirements
- **Types:** `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `build`, `ci`
- **Scope:** Optional but preferred (module, feature, or file area)
- **Summary:** Imperative mood (e.g., "add", "fix", "update"), max 72 characters, no trailing period
- **Body (ONLY if needed):** Explain WHY, not WHAT. Include context, trade-offs, or side-effects
- **Footer (if applicable):** `BREAKING CHANGE: <description>`, `Closes #<issue-number>`

### Rules
- Avoid vague messages like "updated code" or "fix stuff"
- Prefer atomic, single-purpose commits
- Infer intent from diff, not just file names
- Highlight user-facing impact when relevant

### Guidance
- Prioritize semantic clarity over brevity when needed
- If multiple logical changes exist, suggest splitting commits
- Identify hidden intent (bug fix vs refactor vs feature)
- Detect and label breaking changes explicitly
- For **refactors**: confirm no behavior change
- For **fixes**: describe root cause if inferable
- For **features**: mention user benefit or capability added
- Maintain consistency with repository commit history style

---

## Pull Request Instructions

Generate a structured pull request description with the following sections:

### Template

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

### Guidance
- Be explicit about intent, not just implementation
- Highlight breaking changes clearly
- Avoid generic summaries like "various fixes"
- Prefer structured formatting over paragraphs
- Use bullet points for readability
- Align tone with professional engineering standards
- Ensure traceability to issues, tickets, or discussions
- Add relevant existing labels to the PR; if no relevant labels exist, create them
