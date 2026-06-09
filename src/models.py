#!/usr/bin/env python3
"""
models.py — ORM State Layer for the Double-Entry Payment Ledger
================================================================

Defines all SQLAlchemy ORM models, enumerations, and database constants.
This module is the **State Layer** — it describes *what* the ledger looks
like, not *how* it behaves.

Educational Ledger Guarantees
-----------------------------
- **BigInteger arithmetic**: All posted money amounts use ``BigInteger``
  minor units (cents for USD/EUR) instead of binary floating point.
- **Optimistic Concurrency Control (OCC)**: The ``Account`` model carries
  a ``version_id`` column configured as SQLAlchemy's version counter.
  Any concurrent modification to the same account row will raise
  ``StaleDataError``.
- **Immutability Guard**: No relationship uses ``cascade="all, delete-orphan"``.
  Foreign keys on the ``entries`` table use ``ondelete="RESTRICT"`` to
  prevent deletion of parent rows at the database level.
"""

from __future__ import annotations

import enum
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Engine,
    Enum,
    event,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
)
from datetime import datetime, timezone

@event.listens_for(Engine, "begin")
def _sqlite_begin_immediate(conn):
    if conn.get_execution_options().get("sqlite_begin_immediate", False):
        conn.exec_driver_sql("BEGIN IMMEDIATE")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONSTANTS & CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DB_PATH = Path(__file__).resolve().parent.parent / "ledger.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


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


class TransactionType(str, enum.Enum):
    """Business category for an append-only journal transaction."""
    PAYMENT = "PAYMENT"
    REVERSAL = "REVERSAL"
    SEED = "SEED"


class EntryDirection(str, enum.Enum):
    """
    Every ledger entry is either a DEBIT or a CREDIT.

    Convention used by this educational simulator:
        DEBIT  → increases the account balance  (funds received / loaded)
        CREDIT → decreases the account balance  (funds sent / withdrawn)

    The arithmetic identity must hold independently per currency.
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

    Optimistic Concurrency Control
    ------------------------------
    The ``version_id`` column is incremented automatically by SQLAlchemy on
    every UPDATE.  If two concurrent transactions attempt to modify the same
    account row, the second will receive a ``StaleDataError``, preventing
    lost updates.

    Attributes
    ----------
    id         : int     – Auto-incrementing primary key.
    name       : str     – Human-readable label (e.g. "Alice", "FX Clearing USD").
    currency   : str     – ISO-4217 currency code (e.g. "USD", "EUR").
    type       : str     – Account classification (USER | CORPORATE_FX_CLEARING).
    version_id : int     – OCC version counter (auto-incremented on UPDATE).
    entries    : list    – Back-reference to all :class:`Entry` rows linked here.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    currency = Column(String(3), nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    version_id = Column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version_id}

    # Relationships — NO cascade delete.  Entries are append-only.
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
    request_fingerprint = Column(String(128), nullable=True)
    transaction_type = Column(
        Enum(TransactionType),
        nullable=False,
        default=TransactionType.PAYMENT,
    )
    reversed_transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Relationships — save-update and merge only.  NO cascade delete.
    # Immutability: entries must never be deleted via cascade.
    entries = relationship(
        "Entry",
        back_populates="transaction",
        lazy="select",
        cascade="save-update, merge",
    )
    fx_quote_snapshot = relationship(
        "FxQuoteSnapshot",
        back_populates="transaction",
        lazy="select",
        uselist=False,
        cascade="save-update, merge",
    )
    reversed_transaction = relationship(
        "Transaction",
        remote_side=[id],
        foreign_keys=[reversed_transaction_id],
        lazy="select",
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

    Immutability
    ------------
    - ``ondelete="RESTRICT"`` on both foreign keys prevents deletion of
      parent Account or Transaction rows while entries reference them.
    - No ``cascade="all, delete-orphan"`` exists on any parent relationship.

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
        ForeignKey("transactions.id", ondelete="RESTRICT"),
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


class FxQuoteSnapshot(Base):
    """
    Immutable exchange-rate snapshot used by a cross-currency transaction.

    The ledger accepts a caller-supplied rate/quote and records the exact
    string used for conversion.  Money amounts remain integer minor units;
    the rate is audit metadata, not a posted ledger amount.
    """
    __tablename__ = "fx_quote_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    rate = Column(String(64), nullable=False)
    provider = Column(String(128), nullable=True)
    quote_id = Column(String(128), nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    rounding_mode = Column(String(32), nullable=False)
    source_amount_minor = Column(BigInteger, nullable=False)
    destination_amount_minor = Column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("source_amount_minor > 0", name="ck_fx_source_positive"),
        CheckConstraint("destination_amount_minor > 0", name="ck_fx_destination_positive"),
        Index("ix_fx_quote_transaction", "transaction_id"),
    )

    transaction = relationship("Transaction", back_populates="fx_quote_snapshot")

    def __repr__(self) -> str:
        return (
            f"FxQuoteSnapshot(txn={self.transaction_id}, "
            f"{self.from_currency}->{self.to_currency} @ {self.rate})"
        )
