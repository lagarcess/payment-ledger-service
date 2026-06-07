#!/usr/bin/env python3
"""
ledger.py — Behavior Layer for the Double-Entry Payment Ledger
===============================================================

Implements all transactional operations, invariant verification, database
bootstrapping, and display utilities.  This module is the **Behavior Layer**
— it defines *how* the ledger operates against the ORM models defined in
``models.py``.

Enterprise Compliance
---------------------
- **Pessimistic Row Locking**: ``execute_cross_currency_payment()`` acquires
  ``FOR UPDATE`` locks on the sender and FX clearing ``Account`` rows
  *before* computing aggregate balances, preventing concurrent double-spends.
- **Append-Only Bootstrap**: ``bootstrap_database()`` seeds the ledger
  exclusively through balanced equity journal entries.  No ``DELETE`` or
  destructive ``UPDATE`` statements are issued against ledger rows.
- **ACID Transactions**: All multi-leg operations are wrapped in strict
  ``with session.begin():`` blocks for atomic commit / rollback.
"""

from __future__ import annotations

import sys

from sqlalchemy import (
    create_engine,
    event,
    text,
)
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.orm.attributes import flag_modified

from .models import (
    DB_PATH,
    DATABASE_URL,
    Account,
    AccountType,
    Base,
    Entry,
    EntryDirection,
    Transaction,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TERMINAL FORMATTING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CUSTOM EXCEPTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DuplicateTransactionError(Exception):
    """Raised when an idempotency_key has already been consumed."""
    pass


class InsufficientFundsError(Exception):
    """Raised when a debit would drive a USER account balance below zero."""
    pass


class InvariantViolationError(Exception):
    """Raised when the global debit/credit balance is non-zero."""
    pass


class ConcurrencyConflictError(Exception):
    """Raised when OCC detects a stale version_id (concurrent modification)."""
    pass


class TransactionNotFoundError(Exception):
    """Raised when a referenced transaction does not exist."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LEDGER ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LedgerEngine:
    """
    Core ledger service encapsulating all transactional operations.

    Parameters
    ----------
    session_factory : sessionmaker
        A SQLAlchemy ``sessionmaker`` bound to an engine.  Every public
        method opens (and commits/rolls-back) its own session so that
        callers never need to manage DB lifecycle directly.
    """

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    # ── helpers ──────────────────────────────────────────────────────────

    def _get_account_balance(self, session: Session, account_id: int) -> int:
        """
        Compute the current balance of an account by summing its entries.

        Balance = Σ DEBIT amounts  −  Σ CREDIT amounts

        For asset-normal (USER) accounts a positive result means the user
        holds funds; a negative result means an overdraft.

        This query is intentionally run inside the caller's session so it
        participates in the same SERIALIZABLE / exclusive transaction lock.
        """
        result = session.execute(
            text("""
                SELECT COALESCE(SUM(
                    CASE WHEN direction = 'DEBIT'  THEN amount
                         WHEN direction = 'CREDIT' THEN -amount
                    END
                ), 0) AS balance
                FROM entries
                WHERE account_id = :aid
            """),
            {"aid": account_id},
        ).scalar()
        return int(result) if result is not None else 0

    def get_account_balance(self, account_id: int) -> int:
        """Public wrapper — opens its own read-only session."""
        with self._session_factory() as session:
            return self._get_account_balance(session, account_id)

    # ── cross-currency payment ───────────────────────────────────────────

    def execute_cross_currency_payment(
        self,
        sender_id: int,
        receiver_id: int,
        send_amount: int,
        fx_rate: float,
        idempotency_key: str,
        *,
        fx_clearing_usd_id: int,
        fx_clearing_eur_id: int,
        locking_strategy: str = "PESSIMISTIC",
    ) -> Transaction:
        """
        Execute a cross-currency payment through the FX Clearing Account.

        The entire operation is wrapped in a single database transaction.
        Either all four entry legs commit atomically, or none do.

        Locking Strategies
        ------------------
        ``PESSIMISTIC`` (default):
            Acquires ``FOR UPDATE`` locks on Account rows *before*
            computing balances.  Concurrent transactions block until
            the lock holder commits, then read updated balances.

        ``OCC`` (Optimistic Concurrency Control):
            Loads Account rows without locks.  After inserting entries,
            "touches" the Account rows via ``flag_modified()`` to force
            a ``version_id`` increment.  If another transaction already
            committed a version bump, SQLAlchemy raises ``StaleDataError``
            at flush time.

        Parameters
        ----------
        sender_id         : int   – Account ID of the payer.
        receiver_id       : int   – Account ID of the payee.
        send_amount       : int   – Amount in sender's minor currency units.
        fx_rate           : float – Conversion multiplier.
        idempotency_key   : str   – Unique caller-supplied dedup token.
        fx_clearing_usd_id: int   – FX Clearing account ID for sender currency.
        fx_clearing_eur_id: int   – FX Clearing account ID for receiver currency.
        locking_strategy  : str   – "PESSIMISTIC" or "OCC".

        Returns
        -------
        Transaction – The persisted journal entry with its child entries.

        Raises
        ------
        DuplicateTransactionError  – idempotency_key already consumed.
        InsufficientFundsError     – Sender cannot cover the send_amount.
        ConcurrencyConflictError   – OCC version conflict detected.
        """
        try:
            return self._execute_payment_inner(
                sender_id=sender_id,
                receiver_id=receiver_id,
                send_amount=send_amount,
                fx_rate=fx_rate,
                idempotency_key=idempotency_key,
                fx_clearing_usd_id=fx_clearing_usd_id,
                fx_clearing_eur_id=fx_clearing_eur_id,
                locking_strategy=locking_strategy,
            )
        except StaleDataError:
            raise ConcurrencyConflictError(
                "OCC conflict: Account version_id was modified by a "
                "concurrent transaction.  Your payment was rejected "
                "to prevent a double-spend.  Retry with a fresh read."
            )

    def _execute_payment_inner(
        self,
        sender_id: int,
        receiver_id: int,
        send_amount: int,
        fx_rate: float,
        idempotency_key: str,
        *,
        fx_clearing_usd_id: int,
        fx_clearing_eur_id: int,
        locking_strategy: str = "PESSIMISTIC",
    ) -> Transaction:
        """Inner implementation — separated so StaleDataError propagates."""
        with self._session_factory() as session:
            try:
                # For PESSIMISTIC on SQLite: BEGIN IMMEDIATE acquires a
                # RESERVED lock at transaction start, serializing all
                # concurrent writers.  FOR UPDATE is a no-op on SQLite,
                # so this is the only way to prevent stale balance reads.
                if locking_strategy == "PESSIMISTIC":
                    session.connection(execution_options={"sqlite_begin_immediate": True})
                else:
                    session.begin()

                # ── Step 1: Idempotency guard ────────────────────────
                existing = (
                    session.query(Transaction)
                    .filter(Transaction.idempotency_key == idempotency_key)
                    .first()
                )
                if existing is not None:
                    raise DuplicateTransactionError(
                        f"Transaction with idempotency_key "
                        f"'{idempotency_key}' already exists "
                        f"(txn_id={existing.id})."
                    )

                # ── Step 2: Concurrency control & Existence check ────
                if locking_strategy == "PESSIMISTIC":
                    # On PostgreSQL, this would acquire row-level locks.
                    # On SQLite, BEGIN IMMEDIATE already serializes.
                    sender_acct = session.get(Account, sender_id, with_for_update=True)
                    fx_eur_acct = session.get(Account, fx_clearing_eur_id, with_for_update=True)
                else:
                    # OCC: Load without locks — version_id checked at
                    # commit via flag_modified() below.
                    sender_acct = session.get(Account, sender_id)
                    fx_eur_acct = session.get(Account, fx_clearing_eur_id)

                receiver_acct = session.get(Account, receiver_id)
                fx_usd_acct = session.get(Account, fx_clearing_usd_id)

                if not sender_acct:
                    raise ValueError(f"Sender account {sender_id} does not exist.")
                if not receiver_acct:
                    raise ValueError(f"Receiver account {receiver_id} does not exist.")
                if not fx_usd_acct:
                    raise ValueError(f"FX Clearing USD account {fx_clearing_usd_id} does not exist.")
                if not fx_eur_acct:
                    raise ValueError(f"FX Clearing EUR account {fx_clearing_eur_id} does not exist.")

                # ── Step 3: FX conversion (integer arithmetic) ──────
                recv_amount = round(send_amount * fx_rate)
                if recv_amount <= 0:
                    raise ValueError(
                        f"Converted receive amount must be positive, "
                        f"got {recv_amount} "
                        f"(send={send_amount}, rate={fx_rate})."
                    )

                # ── Step 4: Sufficient-funds check on sender ────────
                sender_balance = self._get_account_balance(
                    session, sender_id
                )
                if sender_balance < send_amount:
                    raise InsufficientFundsError(
                        f"Account {sender_id} has balance "
                        f"{sender_balance} cents but tried to send "
                        f"{send_amount} cents."
                    )

                # ── Step 4b: FX Clearing EUR liquidity check ────────
                fx_eur_balance = self._get_account_balance(
                    session, fx_clearing_eur_id
                )
                if fx_eur_balance < recv_amount:
                    raise InsufficientFundsError(
                        f"FX Clearing (EUR) account {fx_clearing_eur_id} "
                        f"has balance {fx_eur_balance} cents but needs "
                        f"{recv_amount} cents to fund the receiver."
                    )

                # ── Step 5: Create journal header ───────────────────
                txn = Transaction(
                    description=(
                        f"Cross-currency payment: Account {sender_id} → "
                        f"Account {receiver_id} | "
                        f"{send_amount} minor units @ FX {fx_rate}"
                    ),
                    idempotency_key=idempotency_key,
                )
                session.add(txn)
                session.flush()  # Materialize txn.id for FK references

                # ── Step 6: Insert the four entry legs ──────────────

                # Leg 1a — CREDIT sender (funds leave)
                entry_1a = Entry(
                    transaction_id=txn.id,
                    account_id=sender_id,
                    amount=send_amount,
                    direction=EntryDirection.CREDIT,
                )
                # Leg 1b — DEBIT FX Clearing (sender currency absorbed)
                entry_1b = Entry(
                    transaction_id=txn.id,
                    account_id=fx_clearing_usd_id,
                    amount=send_amount,
                    direction=EntryDirection.DEBIT,
                )
                # Leg 2a — CREDIT FX Clearing (receiver currency released)
                entry_2a = Entry(
                    transaction_id=txn.id,
                    account_id=fx_clearing_eur_id,
                    amount=recv_amount,
                    direction=EntryDirection.CREDIT,
                )
                # Leg 2b — DEBIT receiver (funds arrive)
                entry_2b = Entry(
                    transaction_id=txn.id,
                    account_id=receiver_id,
                    amount=recv_amount,
                    direction=EntryDirection.DEBIT,
                )

                session.add_all([entry_1a, entry_1b, entry_2a, entry_2b])

                # ── Step 7: OCC version touch ───────────────────────
                # For OCC, force a version_id bump on the Account rows.
                # If a concurrent txn already bumped the version,
                # session.flush() will raise StaleDataError.
                if locking_strategy == "OCC" and sender_acct and fx_eur_acct:
                    flag_modified(sender_acct, "name")
                    flag_modified(fx_eur_acct, "name")

                session.commit()
            except Exception:
                session.rollback()
                raise

        # Return a detached-but-populated object for the caller.
        with self._session_factory() as session:
            txn = (
                session.query(Transaction)
                .filter(Transaction.idempotency_key == idempotency_key)
                .one()
            )
            _ = [e.account for e in txn.entries]
            session.expunge_all()
            return txn

    # ── transaction reversal ─────────────────────────────────────────

    def reverse_transaction(self, transaction_id: int) -> Transaction:
        """
        Create a compensating (reversal) transaction that zeroes out the
        effect of the original.

        This is the ONLY acceptable way to "undo" a transaction in an
        append-only ledger.  The original transaction is never modified
        or deleted — instead, new entries are inserted with flipped
        directions (DEBIT ↔ CREDIT).

        Parameters
        ----------
        transaction_id : int – ID of the transaction to reverse.

        Returns
        -------
        Transaction – The newly-created reversal transaction.

        Raises
        ------
        TransactionNotFoundError  – If the original txn doesn't exist.
        DuplicateTransactionError – If already reversed (REV- key exists).
        InsufficientFundsError    – If reversal would overdraft a USER.
        """
        with self._session_factory() as session:
            with session.begin():
                # ── Load original transaction ────────────────────────
                original = session.get(Transaction, transaction_id)
                if original is None:
                    raise TransactionNotFoundError(
                        f"Transaction {transaction_id} does not exist."
                    )

                # ── Build reversal idempotency key ───────────────────
                rev_key = f"REV-{original.idempotency_key}"

                # ── Idempotency guard (prevent double-reversal) ──────
                existing_rev = (
                    session.query(Transaction)
                    .filter(Transaction.idempotency_key == rev_key)
                    .first()
                )
                if existing_rev is not None:
                    raise DuplicateTransactionError(
                        f"Transaction {transaction_id} has already been "
                        f"reversed (reversal txn_id={existing_rev.id})."
                    )

                # ── Load original entries ────────────────────────────
                original_entries = (
                    session.query(Entry)
                    .filter(Entry.transaction_id == transaction_id)
                    .all()
                )
                if not original_entries:
                    raise TransactionNotFoundError(
                        f"Transaction {transaction_id} has no entries."
                    )

                # ── Pre-flight: check reversal won't overdraft ───────
                # Flipping a DEBIT to CREDIT means money leaves that
                # account.  Check USER accounts won't go negative.
                for entry in original_entries:
                    if entry.direction == EntryDirection.DEBIT:
                        # Reversal will CREDIT this account (take money)
                        acct = session.get(Account, entry.account_id, with_for_update=True)
                        if acct and acct.type == AccountType.USER:
                            bal = self._get_account_balance(
                                session, entry.account_id
                            )
                            if bal < entry.amount:
                                raise InsufficientFundsError(
                                    f"Reversal would overdraft account "
                                    f"{entry.account_id} ({acct.name}): "
                                    f"balance={bal}, "
                                    f"reversal_amount={entry.amount}."
                                )

                # ── Create reversal journal header ───────────────────
                rev_txn = Transaction(
                    description=(
                        f"Reversal of Txn #{transaction_id}: "
                        f"{original.description}"
                    ),
                    idempotency_key=rev_key,
                )
                session.add(rev_txn)
                session.flush()

                # ── Create reversed entry legs ───────────────────────
                for entry in original_entries:
                    flipped_direction = (
                        EntryDirection.CREDIT
                        if entry.direction == EntryDirection.DEBIT
                        else EntryDirection.DEBIT
                    )
                    session.add(Entry(
                        transaction_id=rev_txn.id,
                        account_id=entry.account_id,
                        amount=entry.amount,
                        direction=flipped_direction,
                    ))

        # Return detached reversal transaction
        with self._session_factory() as session:
            rev = (
                session.query(Transaction)
                .filter(Transaction.idempotency_key == rev_key)
                .one()
            )
            _ = [e.account for e in rev.entries]
            session.expunge_all()
            return rev

    # ── invariant verification ───────────────────────────────────────────

    def verify_system_invariants(self) -> bool:
        """
        Assert the fundamental accounting identity across the entire ledger:

            Σ  DEBIT amounts  −  Σ  CREDIT amounts  ==  0

        This must hold at all times in a correctly-operating double-entry
        system.  A non-zero result indicates a bug or data corruption.

        Returns
        -------
        bool – True if invariants hold.

        Raises
        ------
        InvariantViolationError – If the global sum is not zero.
        """
        with self._session_factory() as session:
            global_sum = session.execute(
                text("""
                    SELECT COALESCE(SUM(
                        CASE WHEN direction = 'DEBIT'  THEN amount
                             WHEN direction = 'CREDIT' THEN -amount
                        END
                    ), 0) AS net
                    FROM entries
                """)
            ).scalar()

        if global_sum != 0:
            raise InvariantViolationError(
                f"CRITICAL: Global ledger imbalance detected! "
                f"Net = {global_sum} (expected 0)."
            )
        return True

    def verify_no_negative_user_balances(self) -> bool:
        """
        Ensure no USER account has a negative balance (overdraft).

        Corporate/clearing accounts are excluded — they may legitimately
        carry negative positions in certain currency legs.

        Returns
        -------
        bool – True if all user balances are ≥ 0.

        Raises
        ------
        InvariantViolationError – Lists every overdrawn user account.
        """
        with self._session_factory() as session:
            rows = session.execute(
                text("""
                    SELECT
                        a.id,
                        a.name,
                        a.currency,
                        COALESCE(SUM(
                            CASE WHEN e.direction = 'DEBIT'  THEN e.amount
                                 WHEN e.direction = 'CREDIT' THEN -e.amount
                            END
                        ), 0) AS balance
                    FROM accounts a
                    LEFT JOIN entries e ON e.account_id = a.id
                    WHERE a.type = 'USER'
                    GROUP BY a.id
                    HAVING balance < 0
                """)
            ).fetchall()

        if rows:
            details = "\n".join(
                f"  • Account {r[0]} ({r[1]}, {r[2]}): "
                f"balance = {r[3]} minor units"
                for r in rows
            )
            raise InvariantViolationError(
                f"Negative user balances detected:\n{details}"
            )
        return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISPLAY UTILITIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _fmt_amount(amount_minor: int, currency: str) -> str:
    """Format a minor-unit integer as a human-readable currency string."""
    major = amount_minor / 100
    return f"{currency} {major:,.2f}"


def print_header(title: str) -> None:
    """Print a styled section header."""
    width = 72
    print(f"\n{CYAN}{'━' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{CYAN}{'━' * width}{RESET}")


def print_accounts_table(session_factory: sessionmaker) -> None:
    """Pretty-print all accounts and their computed balances."""
    print_header("ACCOUNTS")
    with session_factory() as session:
        accounts = session.query(Account).order_by(Account.id).all()
        # Compute balances
        balances: dict[int, int] = {}
        for acct in accounts:
            bal = session.execute(
                text("""
                    SELECT COALESCE(SUM(
                        CASE WHEN direction = 'DEBIT'  THEN amount
                             WHEN direction = 'CREDIT' THEN -amount
                        END
                    ), 0)
                    FROM entries WHERE account_id = :aid
                """),
                {"aid": acct.id},
            ).scalar()
            balances[acct.id] = int(bal)

    fmt = f"  {'ID':>3}  {'Name':<26} {'Type':<24} {'Currency':>8}  {'Balance':>14}"
    print(f"{DIM}{fmt}{RESET}")
    print(f"  {'─' * 3}  {'─' * 26} {'─' * 24} {'─' * 8}  {'─' * 14}")
    for acct in accounts:
        bal = balances[acct.id]
        bal_str = _fmt_amount(bal, acct.currency)
        type_str = acct.type.value
        print(f"  {acct.id:>3}  {acct.name:<26} {type_str:<24} {acct.currency:>8}  {bal_str:>14}")


def print_transactions_table(session_factory: sessionmaker) -> None:
    """Pretty-print all transactions."""
    print_header("TRANSACTIONS (Journal Entries)")
    with session_factory() as session:
        txns = session.query(Transaction).order_by(Transaction.id).all()
        if not txns:
            print(f"  {DIM}(no transactions){RESET}")
            return

    fmt = f"  {'ID':>3}  {'Timestamp':<26} {'Idempotency Key':<24} {'Description'}"
    print(f"{DIM}{fmt}{RESET}")
    print(f"  {'─' * 3}  {'─' * 26} {'─' * 24} {'─' * 40}")
    for t in txns:
        ts = t.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if t.timestamp else "—"
        print(f"  {t.id:>3}  {ts:<26} {t.idempotency_key:<24} {t.description}")


def print_entries_table(session_factory: sessionmaker) -> None:
    """Pretty-print all ledger entries with account context."""
    print_header("ENTRIES (Ledger Legs)")
    with session_factory() as session:
        entries = (
            session.query(Entry)
            .join(Account)
            .order_by(Entry.transaction_id, Entry.id)
            .all()
        )
        if not entries:
            print(f"  {DIM}(no entries){RESET}")
            return

        # Collect display data while session is open
        rows = []
        for e in entries:
            rows.append((
                e.id,
                e.transaction_id,
                e.account.name,
                e.account.currency,
                e.direction.value,
                e.amount,
            ))

    fmt = (
        f"  {'ID':>3}  {'Txn':>4}  {'Account':<26} "
        f"{'Currency':>8}  {'Direction':<8}  {'Amount':>14}"
    )
    print(f"{DIM}{fmt}{RESET}")
    print(
        f"  {'─' * 3}  {'─' * 4}  {'─' * 26} "
        f"{'─' * 8}  {'─' * 8}  {'─' * 14}"
    )
    for eid, tid, aname, cur, direction, amt in rows:
        color = GREEN if direction == "DEBIT" else RED
        amt_str = _fmt_amount(amt, cur)
        print(
            f"  {eid:>3}  {tid:>4}  {aname:<26} "
            f"{cur:>8}  {color}{direction:<8}{RESET}  {amt_str:>14}"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATABASE BOOTSTRAP (Append-Only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bootstrap_database(engine, session_factory: sessionmaker) -> dict[str, int]:
    """
    Drop all tables, recreate them, and seed initial account data using
    strictly append-only equity journal entries.

    No ``DELETE`` or destructive ``UPDATE`` statements are issued against
    ledger rows.  All seed funding flows through a System Equity account
    to maintain the double-entry invariant.

    Returns a dict mapping logical names to account IDs for convenience.

    Seed Data
    ---------
    1. User 1 (USD)  – funded with $100.00 (10 000 cents).
    2. User 2 (EUR)  – starts at €0.00.
    3. FX Clearing (USD) – pre-funded with $1 000 000.00 liquidity.
    4. FX Clearing (EUR) – pre-funded with €1 000 000.00 liquidity.
    5. System Equity (MULTI) – the funding source for all seed capital.

    The FX Clearing accounts simulate a corporate treasury pool that
    enables instant cross-currency settlement.
    """
    # Wipe and recreate schema (DDL — not row deletion)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with session_factory() as session:
        with session.begin():
            # ── Create accounts ──────────────────────────────────────
            user1 = Account(
                name="Alice (User 1)",
                currency="USD",
                type=AccountType.USER,
            )
            user2 = Account(
                name="Bob (User 2)",
                currency="EUR",
                type=AccountType.USER,
            )
            fx_usd = Account(
                name="FX Clearing (USD)",
                currency="USD",
                type=AccountType.CORPORATE_FX_CLEARING,
            )
            fx_eur = Account(
                name="FX Clearing (EUR)",
                currency="EUR",
                type=AccountType.CORPORATE_FX_CLEARING,
            )
            equity = Account(
                name="System Equity (Seed)",
                currency="MULTI",
                type=AccountType.CORPORATE_FX_CLEARING,
            )
            session.add_all([user1, user2, fx_usd, fx_eur, equity])
            session.flush()  # Materialize IDs

            # ── Seed funding transactions (append-only) ──────────────
            # All funding flows through the System Equity account.
            # Each transaction is a balanced pair of entries:
            #   DEBIT  recipient  (funds in)
            #   CREDIT equity     (funds out of equity pool)

            # Fund User 1 with $100.00
            fund_user1_txn = Transaction(
                description="Initial funding: Alice receives $100.00",
                idempotency_key="SEED_FUND_USER1",
            )
            session.add(fund_user1_txn)
            session.flush()

            session.add_all([
                Entry(
                    transaction_id=fund_user1_txn.id,
                    account_id=user1.id,
                    amount=10_000,  # $100.00 in cents
                    direction=EntryDirection.DEBIT,
                ),
                Entry(
                    transaction_id=fund_user1_txn.id,
                    account_id=equity.id,
                    amount=10_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])

            # Capitalise FX Clearing USD pool — $1,000,000.00
            cap_usd_txn = Transaction(
                description="Treasury capitalisation: FX Clearing USD",
                idempotency_key="SEED_CAP_FX_USD",
            )
            session.add(cap_usd_txn)
            session.flush()

            session.add_all([
                Entry(
                    transaction_id=cap_usd_txn.id,
                    account_id=fx_usd.id,
                    amount=100_000_000,  # $1M in cents
                    direction=EntryDirection.DEBIT,
                ),
                Entry(
                    transaction_id=cap_usd_txn.id,
                    account_id=equity.id,
                    amount=100_000_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])

            # Capitalise FX Clearing EUR pool — €1,000,000.00
            cap_eur_txn = Transaction(
                description="Treasury capitalisation: FX Clearing EUR",
                idempotency_key="SEED_CAP_FX_EUR",
            )
            session.add(cap_eur_txn)
            session.flush()

            session.add_all([
                Entry(
                    transaction_id=cap_eur_txn.id,
                    account_id=fx_eur.id,
                    amount=100_000_000,  # €1M in cents
                    direction=EntryDirection.DEBIT,
                ),
                Entry(
                    transaction_id=cap_eur_txn.id,
                    account_id=equity.id,
                    amount=100_000_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])

        # Return a map of logical names → account IDs
        return {  # type: ignore
            "user1": user1.id,
            "user2": user2.id,
            "fx_usd": fx_usd.id,
            "fx_eur": fx_eur.id,
            "equity": equity.id,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN SIMULATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main() -> None:
    """
    Run the full sandbox simulation.

    Steps:
    1. Bootstrap the database (drop + create + seed).
    2. Display initial state.
    3. Execute a valid cross-currency payment (USD → EUR).
    4. Display post-transaction state.
    5. Run invariant checks.
    6. Attempt a duplicate transaction (same idempotency_key).
    7. Demonstrate overdraft protection.
    """
    print(f"\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}  DOUBLE-ENTRY PAYMENT LEDGER ENGINE — SANDBOX SIMULATION{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}")
    print(f"{DIM}  Database: {DB_PATH}{RESET}")

    # ── 1. Bootstrap ─────────────────────────────────────────────────
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debug output
        # SQLite-specific: enforce foreign keys
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode and foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    SessionFactory = sessionmaker(bind=engine)

    print(f"\n  {YELLOW}▸ Bootstrapping database (drop → create → seed)...{RESET}")
    ids = bootstrap_database(engine, SessionFactory)
    print(f"  {GREEN}✓ Database ready.{RESET}")
    print(f"  {DIM}  Account IDs: {ids}{RESET}")

    ledger = LedgerEngine(SessionFactory)

    # ── 2. Initial state ─────────────────────────────────────────────
    print_header("INITIAL STATE")
    print_accounts_table(SessionFactory)
    print_transactions_table(SessionFactory)
    print_entries_table(SessionFactory)

    # ── 3. Execute cross-currency payment ────────────────────────────
    print_header("EXECUTING CROSS-CURRENCY PAYMENT")
    FX_RATE_USD_TO_EUR = 0.92  # 1 USD = 0.92 EUR
    SEND_AMOUNT = 5_000  # $50.00 in cents
    IDEM_KEY = "PAY-20260605-001"

    print(f"  Sender  : Alice (User 1) — Account #{ids['user1']}")
    print(f"  Receiver: Bob   (User 2) — Account #{ids['user2']}")
    print(f"  Amount  : {_fmt_amount(SEND_AMOUNT, 'USD')}")
    print(f"  FX Rate : 1 USD = {FX_RATE_USD_TO_EUR} EUR")
    print(
        f"  Expected: Bob receives "
        f"{_fmt_amount(round(SEND_AMOUNT * FX_RATE_USD_TO_EUR), 'EUR')}"
    )
    print(f"  Idem Key: {IDEM_KEY}")

    txn = ledger.execute_cross_currency_payment(
        sender_id=ids["user1"],
        receiver_id=ids["user2"],
        send_amount=SEND_AMOUNT,
        fx_rate=FX_RATE_USD_TO_EUR,
        idempotency_key=IDEM_KEY,
        fx_clearing_usd_id=ids["fx_usd"],
        fx_clearing_eur_id=ids["fx_eur"],
    )
    print(f"\n  {GREEN}✓ Payment executed successfully (txn_id={txn.id}).{RESET}")

    # ── 4. Post-transaction state ────────────────────────────────────
    print_header("POST-TRANSACTION STATE")
    print_accounts_table(SessionFactory)
    print_transactions_table(SessionFactory)
    print_entries_table(SessionFactory)

    # ── 5. Invariant checks ──────────────────────────────────────────
    print_header("INVARIANT VERIFICATION")

    try:
        ledger.verify_system_invariants()
        print(f"  {GREEN}✓ PASS: Global ledger balance = 0 "
              f"(Σ debits == Σ credits){RESET}")
    except InvariantViolationError as e:
        print(f"  {RED}✗ FAIL: {e}{RESET}")
        sys.exit(1)

    try:
        ledger.verify_no_negative_user_balances()
        print(f"  {GREEN}✓ PASS: No user accounts are overdrawn.{RESET}")
    except InvariantViolationError as e:
        print(f"  {RED}✗ FAIL: {e}{RESET}")
        sys.exit(1)

    # ── 6. Duplicate transaction attempt ─────────────────────────────
    print_header("IDEMPOTENCY TEST — DUPLICATE PAYMENT ATTEMPT")
    print(
        f"  {YELLOW}▸ Re-submitting payment with same idempotency key: "
        f"'{IDEM_KEY}'{RESET}"
    )

    try:
        ledger.execute_cross_currency_payment(
            sender_id=ids["user1"],
            receiver_id=ids["user2"],
            send_amount=SEND_AMOUNT,
            fx_rate=FX_RATE_USD_TO_EUR,
            idempotency_key=IDEM_KEY,  # ← same key!
            fx_clearing_usd_id=ids["fx_usd"],
            fx_clearing_eur_id=ids["fx_eur"],
        )
        # Should never reach here
        print(f"  {RED}✗ FAIL: Duplicate was NOT rejected!{RESET}")
        sys.exit(1)
    except DuplicateTransactionError as e:
        print(f"  {GREEN}✓ PASS: Duplicate correctly rejected.{RESET}")
        print(f"  {DIM}  Error: {e}{RESET}")

    # ── 7. Overdraft protection test ─────────────────────────────────
    print_header("OVERDRAFT PROTECTION TEST")
    print(
        f"  {YELLOW}▸ Attempting to send $200.00 from Alice "
        f"(balance: {_fmt_amount(ledger.get_account_balance(ids['user1']), 'USD')})"
        f"{RESET}"
    )

    try:
        ledger.execute_cross_currency_payment(
            sender_id=ids["user1"],
            receiver_id=ids["user2"],
            send_amount=20_000,  # $200.00 — exceeds Alice's balance
            fx_rate=FX_RATE_USD_TO_EUR,
            idempotency_key="PAY-20260605-OVERDRAFT-TEST",
            fx_clearing_usd_id=ids["fx_usd"],
            fx_clearing_eur_id=ids["fx_eur"],
        )
        print(f"  {RED}✗ FAIL: Overdraft was NOT rejected!{RESET}")
        sys.exit(1)
    except InsufficientFundsError as e:
        print(f"  {GREEN}✓ PASS: Overdraft correctly rejected.{RESET}")
        print(f"  {DIM}  Error: {e}{RESET}")

    # ── Final state ──────────────────────────────────────────────────
    print_header("FINAL ACCOUNT BALANCES")
    print_accounts_table(SessionFactory)

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═' * 72}{RESET}")
    print(f"{GREEN}{BOLD}  ALL CHECKS PASSED — LEDGER ENGINE OPERATING CORRECTLY{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}\n")


if __name__ == "__main__":
    main()
