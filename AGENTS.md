# Agent Instructions: Lightspark Payment Service

Welcome! You are operating in the `lightspark-payment-service` codebase. This is a double-entry payment ledger engine designed to execute cross-currency transfers. 

## Technology Stack
- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Vanilla HTML5, JavaScript, CSS (No JS frameworks)
- **Dependency Management:** Poetry (`pyproject.toml`)
- **Key Files:**
  - `sandbox_ledger.py`: Core ledger logic, double-entry accounting, invariant checks, database setup.
  - `api.py`: FastAPI server exposing endpoints for state, payment execution, and reset.
  - `static/`: Frontend assets (`index.html`, `style.css`, `script.js`).

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

## Development Workflow

### Running the App
The project uses Poetry. Run commands using `poetry run`.

1. **Seed/Reset the database:**
   ```bash
   poetry run python sandbox_ledger.py
   ```
2. **Start the development server:**
   ```bash
   poetry run uvicorn api:app --reload
   ```

The dashboard will be available at `http://127.0.0.1:8000/`.

### Modifying the Frontend
- The frontend is located in the `static/` directory.
- It uses vanilla HTML/JS/CSS. Do not introduce frameworks like React or Tailwind unless explicitly requested by the user.
- The `DESIGN.md` file contains design guidelines and analysis (a sleek dark interface, gradient cards, fintech precision). Consult this file before making UI or aesthetic changes.

### Making Changes
- **Database Schema:** If you change the SQLAlchemy models in `sandbox_ledger.py`, you may need to recreate the database (the `/api/reset` endpoint or running `sandbox_ledger.py` directly handles dropping and recreating tables).
- **Testing:** Ensure any new transaction types strictly preserve the double-entry principles and the global system invariant of zero.
