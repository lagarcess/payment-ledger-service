#!/usr/bin/env python3
"""
sandbox_ledger.py — Double-Entry Payment Ledger Engine (Educational Sandbox)
=============================================================================

A self-contained, runnable simulation of a production-grade double-entry
ledger with cross-currency FX clearing, idempotency protection, and
system-wide invariant verification.

Architecture Overview
---------------------
Every monetary movement is recorded as a balanced *Transaction* (journal
entry) containing two or more *Entry* legs.  The fundamental accounting
identity enforced at all times is:

    Σ debits  ==  Σ credits   (globally, and per transaction)

Cross-currency payments are routed through a **Corporate FX Clearing
Account** that absorbs currency conversion risk and maintains liquidity
pools in each supported currency.

    ┌──────────┐       Leg 1 (USD)        ┌─────────────────────┐
    │  User A  │ ──── DEBIT ──────────▶   │  FX Clearing (USD)  │
    │  (USD)   │                CREDIT ◀── │                     │
    └──────────┘                          └─────────────────────┘
                                                    │
                                          Leg 2 (EUR)│
                                                    ▼
    ┌──────────┐                          ┌─────────────────────┐
    │  User B  │ ◀──── CREDIT ────────── │  FX Clearing (EUR)  │
    │  (EUR)   │                DEBIT ──▶ │                     │
    └──────────┘                          └─────────────────────┘

Run
---
    python sandbox_ledger.py

Requirements: Python 3.10+, SQLAlchemy (pip install sqlalchemy)
"""

from __future__ import annotations

import enum
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    relationship,
    sessionmaker,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONSTANTS & CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DB_PATH = Path(__file__).resolve().parent.parent / "ledger.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Terminal formatting helpers
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENUMERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AccountType(str, enum.Enum):
    """
    Classification of ledger accounts.

    USER                  – End-user wallets holding real balances.
    CORPORATE_FX_CLEARING – Internal house account used to absorb FX
                            conversion legs.  Operates as a liquidity pool
                            and must be pre-funded in every supported currency.
    """
    USER = "USER"
    CORPORATE_FX_CLEARING = "CORPORATE_FX_CLEARING"


class EntryDirection(str, enum.Enum):
    """
    Every ledger entry is either a DEBIT (money leaving an account in
    double-entry terms) or a CREDIT (money entering).

    Convention used here (asset-normal accounts):
        DEBIT  → increases the account balance  (funds received / loaded)
        CREDIT → decreases the account balance  (funds sent / withdrawn)

    For liability / clearing accounts the semantics invert, but the
    arithmetic identity  Σ DEBIT == Σ CREDIT  always holds globally.
    """
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ORM MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


class Account(Base):
    """
    Represents a monetary account in the ledger.

    Each account is denominated in a single ISO-4217 currency code and is
    classified by its :class:`AccountType`.

    Attributes
    ----------
    id       : int     – Auto-incrementing primary key.
    name     : str     – Human-readable label (e.g. "Alice", "FX Clearing USD").
    currency : str     – ISO-4217 currency code (e.g. "USD", "EUR").
    type     : str     – Account classification (USER | CORPORATE_FX_CLEARING).
    entries  : list    – Back-reference to all :class:`Entry` rows linked here.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    currency = Column(String(3), nullable=False)
    type = Column(Enum(AccountType), nullable=False)

    # Relationships
    entries = relationship("Entry", back_populates="account", lazy="select")

    def __repr__(self) -> str:
        return (
            f"Account(id={self.id}, name='{self.name}', "
            f"currency='{self.currency}', type='{self.type.value}')"
        )


class Transaction(Base):
    """
    Journal entry header — groups one or more balanced :class:`Entry` legs.

    The ``idempotency_key`` column carries a UNIQUE constraint so that the
    same logical payment can never be recorded twice, even under concurrent
    retries or network replays.

    Attributes
    ----------
    id              : int      – Auto-incrementing primary key.
    timestamp       : datetime – UTC wall-clock time of journal creation.
    description     : str      – Free-text narrative of the business event.
    idempotency_key : str      – Caller-supplied unique token (UNIQUE constraint).
    entries         : list     – Child :class:`Entry` legs belonging to this txn.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    description = Column(String(512), nullable=False)
    idempotency_key = Column(String(256), nullable=False, unique=True)

    # Relationships
    entries = relationship(
        "Entry",
        back_populates="transaction",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.id}, key='{self.idempotency_key}', "
            f"desc='{self.description}')"
        )


class Entry(Base):
    """
    A single debit or credit leg within a :class:`Transaction`.

    CRITICAL DESIGN DECISION — **integer arithmetic only**.
    The ``amount`` column stores values in the currency's minor unit
    (e.g. cents for USD, euro-cents for EUR).  This eliminates IEEE-754
    floating-point rounding errors that plague naïve financial systems.

    Attributes
    ----------
    id             : int    – Auto-incrementing primary key.
    transaction_id : int    – FK to the parent :class:`Transaction`.
    account_id     : int    – FK to the :class:`Account` affected.
    amount         : int    – Value in minor currency units (MUST be > 0).
    direction      : str    – DEBIT or CREDIT.
    """
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # BigInteger to safely handle large sums without overflow at the DB level.
    amount = Column(BigInteger, nullable=False)
    direction = Column(Enum(EntryDirection), nullable=False)

    # Database-level guard: amounts must always be positive.  The sign
    # semantics are carried entirely by the ``direction`` column.
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_entry_positive_amount"),
        Index("ix_entry_account", "account_id"),
        Index("ix_entry_transaction", "transaction_id"),
    )

    # Relationships
    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account", back_populates="entries")

    def __repr__(self) -> str:
        return (
            f"Entry(id={self.id}, txn={self.transaction_id}, "
            f"acct={self.account_id}, {self.direction.value} "
            f"{self.amount})"
        )


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
        return int(result)

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
    ) -> Transaction:
        """
        Execute a cross-currency payment through the FX Clearing Account.

        The entire operation is wrapped in a single database transaction.
        Either all four entry legs commit atomically, or none do.

        Parameters
        ----------
        sender_id         : int   – Account ID of the payer (e.g. USD user).
        receiver_id       : int   – Account ID of the payee (e.g. EUR user).
        send_amount       : int   – Amount in sender's minor currency units.
        fx_rate           : float – Conversion multiplier (recv_minor / send_minor).
        idempotency_key   : str   – Unique caller-supplied dedup token.
        fx_clearing_usd_id: int   – FX Clearing account ID for sender currency.
        fx_clearing_eur_id: int   – FX Clearing account ID for receiver currency.

        Returns
        -------
        Transaction – The persisted journal entry with its child entries.

        Raises
        ------
        DuplicateTransactionError – If the idempotency_key already exists.
        InsufficientFundsError    – If sender cannot cover the send_amount.

        Detailed Flow
        -------------
        1.  Check idempotency_key against existing transactions.
        2.  Compute the received amount:  recv_amount = round(send_amount × fx_rate)
        3.  Verify sender has sufficient funds.
        4.  Create journal header (Transaction).
        5.  Insert four Entry legs:
              Leg 1a — CREDIT sender       (send_amount in sender currency)
              Leg 1b — DEBIT  FX Clearing   (send_amount in sender currency)
              Leg 2a — CREDIT FX Clearing   (recv_amount in receiver currency)
              Leg 2b — DEBIT  receiver      (recv_amount in receiver currency)
        6.  Commit.
        """
        with self._session_factory() as session:
            with session.begin():
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

                # ── Step 2: FX conversion (integer arithmetic) ──────
                recv_amount = round(send_amount * fx_rate)
                if recv_amount <= 0:
                    raise ValueError(
                        f"Converted receive amount must be positive, "
                        f"got {recv_amount} "
                        f"(send={send_amount}, rate={fx_rate})."
                    )

                # ── Step 3: Sufficient-funds check on sender ────────
                sender_balance = self._get_account_balance(session, sender_id)
                if sender_balance < send_amount:
                    raise InsufficientFundsError(
                        f"Account {sender_id} has balance "
                        f"{sender_balance} cents but tried to send "
                        f"{send_amount} cents."
                    )

                # ── Step 3b: FX Clearing EUR liquidity check ────────
                fx_eur_balance = self._get_account_balance(
                    session, fx_clearing_eur_id
                )
                if fx_eur_balance < recv_amount:
                    raise InsufficientFundsError(
                        f"FX Clearing (EUR) account {fx_clearing_eur_id} "
                        f"has balance {fx_eur_balance} cents but needs "
                        f"{recv_amount} cents to fund the receiver."
                    )

                # ── Step 4: Create journal header ───────────────────
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

                # ── Step 5: Insert the four entry legs ──────────────

                # Leg 1a — Sender parts with funds (CREDIT decreases
                #          an asset-normal account).
                entry_1a = Entry(
                    transaction_id=txn.id,
                    account_id=sender_id,
                    amount=send_amount,
                    direction=EntryDirection.CREDIT,
                )
                # Leg 1b — FX Clearing absorbs those funds (DEBIT
                #          increases the clearing pool in sender currency).
                entry_1b = Entry(
                    transaction_id=txn.id,
                    account_id=fx_clearing_usd_id,
                    amount=send_amount,
                    direction=EntryDirection.DEBIT,
                )
                # Leg 2a — FX Clearing releases converted funds
                #          (CREDIT decreases the EUR pool).
                entry_2a = Entry(
                    transaction_id=txn.id,
                    account_id=fx_clearing_eur_id,
                    amount=recv_amount,
                    direction=EntryDirection.CREDIT,
                )
                # Leg 2b — Receiver gets paid (DEBIT increases their
                #          asset-normal account).
                entry_2b = Entry(
                    transaction_id=txn.id,
                    account_id=receiver_id,
                    amount=recv_amount,
                    direction=EntryDirection.DEBIT,
                )

                session.add_all([entry_1a, entry_1b, entry_2a, entry_2b])

                # ── Step 6: Commit is handled by the context manager ─
                # session.begin() will auto-commit when the block exits
                # without an exception, or auto-rollback on error.

        # Return a detached-but-populated object for the caller to inspect.
        # Re-fetch so relationships are loaded cleanly.
        with self._session_factory() as session:
            txn = (
                session.query(Transaction)
                .filter(Transaction.idempotency_key == idempotency_key)
                .one()
            )
            # Eagerly touch the entries so they're usable after detach.
            _ = [e.account for e in txn.entries]
            session.expunge_all()
            return txn

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
#  DATABASE BOOTSTRAP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bootstrap_database(engine, session_factory: sessionmaker) -> dict[str, int]:
    """
    Drop all tables, recreate them, and seed initial account data.

    Returns a dict mapping logical names to account IDs for convenience.

    Seed Data
    ---------
    1. User 1 (USD)  – funded with $100.00 (10 000 cents).
    2. User 2 (EUR)  – starts at €0.00.
    3. FX Clearing (USD) – pre-funded with $1 000 000.00 liquidity.
    4. FX Clearing (EUR) – pre-funded with €1 000 000.00 liquidity.

    The FX Clearing accounts simulate a corporate treasury pool that
    enables instant cross-currency settlement.
    """
    # Wipe and recreate schema
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
            session.add_all([user1, user2, fx_usd, fx_eur])
            session.flush()  # Materialize IDs

            # ── Seed funding transactions ────────────────────────────
            # These are "external funding" journal entries that bring
            # money into the system.  Each is perfectly balanced:
            # DEBIT the recipient, CREDIT a corresponding source.

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
                    account_id=fx_usd.id,
                    amount=10_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])

            # Fund FX Clearing USD with $1,000,000.00
            fund_fx_usd_txn = Transaction(
                description="Treasury funding: FX Clearing USD pool",
                idempotency_key="SEED_FUND_FX_USD",
            )
            session.add(fund_fx_usd_txn)
            session.flush()

            session.add_all([
                Entry(
                    transaction_id=fund_fx_usd_txn.id,
                    account_id=fx_usd.id,
                    amount=100_000_000,  # $1M in cents
                    direction=EntryDirection.DEBIT,
                ),
                # Balanced against a notional external source — in a real
                # system this would be a bank settlement account.  Here we
                # model it as a self-balancing credit on the same account
                # purely to maintain the invariant for seeding purposes.
                # A production system would have an "External Settlement"
                # account.  For this sandbox we credit User1's clearing
                # symmetry partner — but to keep it clean, we use a
                # dedicated "SYSTEM_SEED" pattern.
                #
                # SIMPLIFICATION: We use a two-legged entry against the
                # same FX clearing account.  This has zero net effect on
                # its balance beyond establishing the audit trail.
                # To truly fund it, we do DEBIT only — and mirror it with
                # a separate accounting trick below.
            ])

            # For a cleaner sandbox, we fund the FX pools via direct
            # balanced entries against each other (USD ↔ EUR).
            # This is the standard "treasury capitalisation" pattern.

            # Remove the half-entry above and use a proper pair:
            session.query(Entry).filter(
                Entry.transaction_id == fund_fx_usd_txn.id
            ).delete()
            session.delete(fund_fx_usd_txn)
            session.flush()

            # Capitalise FX USD pool — balanced against FX EUR pool
            cap_txn = Transaction(
                description=(
                    "Treasury capitalisation: "
                    "FX pools funded with initial liquidity"
                ),
                idempotency_key="SEED_CAPITALISE_FX",
            )
            session.add(cap_txn)
            session.flush()

            session.add_all([
                Entry(
                    transaction_id=cap_txn.id,
                    account_id=fx_usd.id,
                    amount=100_000_000,  # $1M
                    direction=EntryDirection.DEBIT,
                ),
                Entry(
                    transaction_id=cap_txn.id,
                    account_id=fx_eur.id,
                    amount=100_000_000,  # €1M
                    direction=EntryDirection.DEBIT,
                ),
                # Balanced by notional equity entries on the same
                # accounts.  In a full Chart of Accounts you'd have
                # an "Owner's Equity" account.  Here we use a balanced
                # pair of credits back to the clearing accounts
                # themselves, netting to the desired funded amount.
                #
                # Correct approach: introduce a SEED equity account.
            ])

            # Actually — let's do this properly with a seed equity account.
            session.query(Entry).filter(
                Entry.transaction_id == cap_txn.id
            ).delete()
            session.delete(cap_txn)
            session.flush()

            # Create a system equity account to serve as the funding source
            equity = Account(
                name="System Equity (Seed)",
                currency="MULTI",
                type=AccountType.CORPORATE_FX_CLEARING,
            )
            session.add(equity)
            session.flush()

            # Fund FX Clearing USD
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
                    amount=100_000_000,
                    direction=EntryDirection.DEBIT,
                ),
                Entry(
                    transaction_id=cap_usd_txn.id,
                    account_id=equity.id,
                    amount=100_000_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])

            # Fund FX Clearing EUR
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
                    amount=100_000_000,
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
        return {
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
    from sqlalchemy import event

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
