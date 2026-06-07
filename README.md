# Ledger Engine

A double-entry payment ledger engine designed to execute cross-currency transfers. It includes a Python backend powered by FastAPI and SQLite, and a clean vanilla HTML/JS/CSS frontend dashboard.

## Key Concepts

This project demonstrates several core fintech and accounting principles used by state-of-the-art banking systems. Here is how they work and where to find them:

### Double-Entry Accounting & System Invariants
Every transaction must be perfectly balanced (`Σ debits == Σ credits`). Instead of simply changing a single account balance, money is always moved from one place to another using equal and opposite journal entries. A core "System Invariant" guarantees that the net balance of the entire universe of accounts is exactly zero at all times.
- **How to see it at play:** Look at the "Entry Legs" table on the dashboard. When a transfer occurs, you will see multiple legs (Debits and Credits) that all sum to exactly zero. You can also monitor the "System Invariant" badge at the top, which constantly verifies the global net balance.
- **Where the code lives:** `src/ledger.py` handles the core math, balancing logic, and global invariant checks.

### Integer Arithmetic (Minor Units)
Floating-point numbers (decimals) are notoriously imprecise in computer science and can lead to microscopic rounding errors. In a financial ledger, a rounding error of even a fraction of a cent is catastrophic.
- **How to see it at play:** The backend processes all amounts as integers representing the smallest unit of the currency (e.g., cents for USD/EUR). $100.00 is stored and calculated strictly as `10000`. The decimal point is only re-introduced by the frontend at the very last second for display purposes.
- **Where the code lives:** `src/models.py` and `src/ledger.py` perform all ledger math strictly using Python integers. `static/script.js` reformats the integer back into a localized currency string.

### Treasury Seeding
A true double-entry ledger cannot simply "create" or "print" money out of thin air to give users a starting balance; doing so would instantly violate the system invariant. 
- **What it emulates:** This mirrors real-life banking, where an institution must first be capitalized by a central bank or equity investors. In our system, the database generates an initial "Genesis Block" that funds a root Treasury account, which then distributes seed capital to the users and the clearing pools.
- **Where the code lives:** Look at the `bootstrap_database()` function in `src/ledger.py`, which meticulously structures the initial capital injection journal entries through append-only equity transactions.

### Cross-Currency FX Clearing
Payments between users with different currencies (e.g., USD to EUR) are not exchanged directly. Instead, they are routed through internal "Corporate FX Clearing" accounts. These treasury pools act as market makers: they buy the sender's currency into their USD pool, and sell the receiver's currency out of their EUR pool. This absorbs the currency conversion risk and isolates liquidity management.
- **How to see it at play:** Execute a transfer from a USD account to a EUR account. The dashboard will automatically generate a visual flow diagram showing the USD leaving the sender, entering the USD Clearing pool, and the equivalent EUR leaving the EUR Clearing pool to the receiver.
- **Where the code lives:** `src/ledger.py` dynamically calculates the exchange rate and creates the intermediate clearing legs during transaction processing. `static/script.js` handles the real-time diagram rendering.

### ACID Database Transactions
If a server crashes exactly halfway through processing a payment (e.g., after the sender's account is debited, but before the receiver's account is credited), the money would vanish into the ether, corrupting the ledger permanently.
- **What it emulates:** We use strict ACID database transactions. A payment is treated as a single atomic unit of work. If any single leg of the transfer fails, or if an overdraft occurs, the *entire* operation is instantly rolled back, guaranteeing the ledger is never left in an invalid or partially-completed state.
- **Where the code lives:** `src/ledger.py` wraps all entry creations inside a strict `with session.begin():` block that rolls back upon any exception.

### Idempotency
Idempotency prevents duplicate transactions. If a user accidentally double-clicks "Send" or a network request drops and is retried, the system ensures the payment only happens exactly once by requiring a unique, single-use key for every request.
- **How to see it at play:** Uncheck "Auto-generate" on the dashboard, type a custom idempotency key, and execute a payment. Try executing it a second time with the exact same key. The system will safely reject the second attempt.
- **Where the code lives:** `src/models.py` enforces a unique database constraint on the key. `src/api.py` catches duplicate errors and returns a 409 status code.

### Overdraft Protection
End-user accounts are never allowed to drop below a zero balance.
- **How to see it at play:** Attempt to send an amount that is larger than the sender's current balance. The transfer will be rejected and an error toast will explain exactly how short the account is.
- **Where the code lives:** `src/ledger.py` strictly checks account balances before creating any ledger entries and raises an `InsufficientFundsError` if the transaction would result in a negative balance.

### Idempotent Environment Reset
In highly complex financial systems, rigorous testing requires an exact, predictable environment state.
- **How to see it at play:** Clicking the "Reset Environment" button completely destroys the current database and reconstructs the ledger from the exact same initial genesis block. This allows developers and testers to reproduce edge cases repeatedly.
- **Where the code lives:** `src/api.py` exposes the `/api/reset` endpoint, which drops the SQLite tables and triggers the seed function in `src/ledger.py`.

## Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite (`src/api.py`, `src/models.py`, `src/ledger.py`)
- **Frontend:** HTML5, Vanilla JavaScript, CSS (`static/index.html`, `static/script.js`, `static/style.css`)

## Getting Started

### Prerequisites

Ensure you have Python 3.10+ installed.

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd lightspark-payment-service
   ```

2. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn sqlalchemy
   ```

3. **Initialize the Ledger:**
   The backend script will automatically seed the SQLite database with initial users and treasury funding upon the first run.
   ```bash
   poetry run python -m src.ledger
   ```

4. **Start the API Server:**
   ```bash
   poetry run uvicorn src.api:app --reload
   ```

5. **Access the Dashboard:**
   Open your browser and navigate to:
   `http://127.0.0.1:8000/`

## API Endpoints

- `GET /api/state`: Returns the entire ledger state (metrics, tables, invariances).
- `POST /api/payment`: Executes a payment payload (requires `sender_id`, `receiver_id`, `send_dollars`, `fx_rate`, `idempotency_key`).
- `POST /api/reset`: Drops the database and reseeds it back to its original state.
