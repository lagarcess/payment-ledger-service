#!/usr/bin/env python3
"""
ledger.py — Behavior Layer for the Double-Entry Payment Ledger
===============================================================

Implements all transactional operations, invariant verification, database
bootstrapping, and display utilities.  This module is the **Behavior Layer**
— it defines *how* the ledger operates against the ORM models defined in
``models.py``.

Educational Simulator Guarantees
--------------------------------
- **Currency-aware invariants**: transaction and system checks balance
  debit/credit totals independently per currency.
- **Append-only bootstrap**: ``bootstrap_database()`` seeds the ledger through
  balanced equity journal entries.  Ordinary corrections use reversals.
- **Concurrency demo paths**: payment execution exposes pessimistic and OCC
  strategies to illustrate tradeoffs in a SQLite-backed simulator.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import sys

from sqlalchemy import (
    create_engine,
    event,
    text,
)
from sqlalchemy.exc import IntegrityError
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
    FxQuoteSnapshot,
    Transaction,
    TransactionType,
)


ROUNDING_MODE = "ROUND_HALF_UP"
VALID_LOCKING_STRATEGIES = {"PESSIMISTIC", "OCC"}
CURRENCY_MINOR_UNITS = {
    "USD": 2,
    "EUR": 2,
}

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


class IdempotencyConflictError(Exception):
    """Raised when a key is reused for a different logical request."""
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

    def _validate_send_amount(self, send_amount: int) -> int:
        if type(send_amount) is not int or send_amount <= 0:
            raise ValueError(
                "send_amount must be a positive integer minor-unit amount."
            )
        return send_amount

    def _validate_locking_strategy(self, locking_strategy: str) -> str:
        normalized = str(locking_strategy).upper()
        if normalized not in VALID_LOCKING_STRATEGIES:
            raise ValueError(
                "locking_strategy must be one of: OCC, PESSIMISTIC."
            )
        return normalized

    def _normalize_decimal_input(self, value: str | Decimal, field_name: str) -> tuple[Decimal, str, str]:
        if not isinstance(value, (str, Decimal)):
            raise ValueError(f"{field_name} must be supplied as a string or Decimal.")

        if isinstance(value, Decimal):
            decimal_value = value
            raw_text = format(value, "f")
        else:
            raw_text = value.strip()
            if not raw_text:
                raise ValueError(f"{field_name} must not be empty.")
            try:
                decimal_value = Decimal(raw_text)
            except InvalidOperation as exc:
                raise ValueError(f"{field_name} must be a valid decimal string.") from exc

        if not decimal_value.is_finite() or decimal_value <= 0:
            raise ValueError(f"{field_name} must be positive.")

        normalized = format(decimal_value.normalize(), "f")
        return decimal_value, raw_text, normalized

    def _minor_unit_quantum(self, currency: str) -> Decimal:
        precision = CURRENCY_MINOR_UNITS.get(currency)
        if precision is None:
            raise ValueError(f"Unsupported currency '{currency}'.")
        return Decimal(1).scaleb(-precision)

    def _convert_minor_units(
        self,
        source_amount_minor: int,
        *,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
    ) -> int:
        from_precision = CURRENCY_MINOR_UNITS.get(from_currency)
        to_precision = CURRENCY_MINOR_UNITS.get(to_currency)
        if from_precision is None:
            raise ValueError(f"Unsupported source currency '{from_currency}'.")
        if to_precision is None:
            raise ValueError(f"Unsupported destination currency '{to_currency}'.")

        source_major = Decimal(source_amount_minor).scaleb(-from_precision)
        destination_major = (source_major * rate).quantize(
            self._minor_unit_quantum(to_currency),
            rounding=ROUND_HALF_UP,
        )
        destination_minor = destination_major.scaleb(to_precision).to_integral_exact()
        return int(destination_minor)

    def _fingerprint(self, payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _payment_fingerprint(
        self,
        *,
        payment_type: str,
        sender_id: int,
        receiver_id: int,
        send_amount: int,
        fx_rate: str | None = None,
        fx_clearing_usd_id: int | None = None,
        fx_clearing_eur_id: int | None = None,
    ) -> str:
        payload: dict[str, object] = {
            "payment_type": payment_type,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "send_amount_minor": send_amount,
        }
        if fx_rate is not None:
            payload["fx_rate"] = fx_rate
        if fx_clearing_usd_id is not None:
            payload["fx_clearing_usd_id"] = fx_clearing_usd_id
        if fx_clearing_eur_id is not None:
            payload["fx_clearing_eur_id"] = fx_clearing_eur_id
        return self._fingerprint(payload)

    def _detach_transaction(self, session: Session, txn: Transaction) -> Transaction:
        _ = [e.account for e in txn.entries]
        _ = txn.fx_quote_snapshot
        session.expunge_all()
        return txn

    def _load_transaction_by_key(self, idempotency_key: str) -> Transaction:
        with self._session_factory() as session:
            txn = (
                session.query(Transaction)
                .filter(Transaction.idempotency_key == idempotency_key)
                .one()
            )
            return self._detach_transaction(session, txn)

    def _handle_existing_idempotency(
        self,
        session: Session,
        existing: Transaction,
        fingerprint: str,
    ) -> Transaction:
        if existing.request_fingerprint == fingerprint:
            return self._detach_transaction(session, existing)

        raise IdempotencyConflictError(
            f"Idempotency key '{existing.idempotency_key}' was already used "
            "for a different payment request."
        )

    def _recover_idempotent_integrity_error(
        self,
        idempotency_key: str,
        fingerprint: str,
        exc: IntegrityError,
    ) -> Transaction:
        with self._session_factory() as session:
            existing = (
                session.query(Transaction)
                .filter(Transaction.idempotency_key == idempotency_key)
                .first()
            )
            if existing is not None:
                if existing.request_fingerprint == fingerprint:
                    return self._detach_transaction(session, existing)
                raise IdempotencyConflictError(
                    f"Idempotency key '{idempotency_key}' was already used "
                    "for a different payment request."
                ) from exc
        raise exc

    def _verify_transaction_balanced_by_currency(self, session: Session, transaction_id: int) -> bool:
        rows = session.execute(
            text("""
                SELECT
                    a.currency,
                    COALESCE(SUM(
                        CASE WHEN e.direction = 'DEBIT'  THEN e.amount
                             WHEN e.direction = 'CREDIT' THEN -e.amount
                        END
                    ), 0) AS net
                FROM entries e
                JOIN accounts a ON a.id = e.account_id
                WHERE e.transaction_id = :tid
                GROUP BY a.currency
                HAVING COALESCE(SUM(
                    CASE WHEN e.direction = 'DEBIT'  THEN e.amount
                         WHEN e.direction = 'CREDIT' THEN -e.amount
                    END
                ), 0) != 0
            """),
            {"tid": transaction_id},
        ).fetchall()

        if rows:
            details = ", ".join(f"{row[0]}={row[1]}" for row in rows)
            raise InvariantViolationError(
                f"Transaction {transaction_id} is not balanced by currency: {details}."
            )
        return True

    def get_currency_invariant_balances(self) -> dict[str, int]:
        """Return signed ledger net by account currency."""
        with self._session_factory() as session:
            rows = session.execute(
                text("""
                    SELECT
                        a.currency,
                        COALESCE(SUM(
                            CASE WHEN e.direction = 'DEBIT'  THEN e.amount
                                 WHEN e.direction = 'CREDIT' THEN -e.amount
                            END
                        ), 0) AS net
                    FROM accounts a
                    LEFT JOIN entries e ON e.account_id = a.id
                    GROUP BY a.currency
                    ORDER BY a.currency
                """)
            ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def get_transaction_currency_imbalances(self) -> list[dict[str, int | str]]:
        """Return transaction-level currency imbalances across the ledger."""
        with self._session_factory() as session:
            rows = session.execute(
                text("""
                    SELECT
                        e.transaction_id,
                        a.currency,
                        COALESCE(SUM(
                            CASE WHEN e.direction = 'DEBIT'  THEN e.amount
                                 WHEN e.direction = 'CREDIT' THEN -e.amount
                            END
                        ), 0) AS net
                    FROM entries e
                    JOIN accounts a ON a.id = e.account_id
                    GROUP BY e.transaction_id, a.currency
                    HAVING COALESCE(SUM(
                        CASE WHEN e.direction = 'DEBIT'  THEN e.amount
                             WHEN e.direction = 'CREDIT' THEN -e.amount
                        END
                    ), 0) != 0
                    ORDER BY e.transaction_id, a.currency
                """)
            ).fetchall()
        return [
            {
                "transaction_id": int(row[0]),
                "currency": str(row[1]),
                "net": int(row[2]),
            }
            for row in rows
        ]

    # ── cross-currency payment ───────────────────────────────────────────

    def execute_cross_currency_payment(
        self,
        sender_id: int,
        receiver_id: int,
        send_amount: int,
        fx_rate: str | Decimal,
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
        fx_rate           : str | Decimal – Conversion multiplier snapshot.
        idempotency_key   : str   – Unique caller-supplied dedup token.
        fx_clearing_usd_id: int   – FX Clearing account ID for sender currency.
        fx_clearing_eur_id: int   – FX Clearing account ID for receiver currency.
        locking_strategy  : str   – "PESSIMISTIC" or "OCC".

        Returns
        -------
        Transaction – The persisted journal entry with its child entries.

        Raises
        ------
        IdempotencyConflictError   – idempotency_key reused for a different request.
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
        fx_rate: str | Decimal,
        idempotency_key: str,
        *,
        fx_clearing_usd_id: int,
        fx_clearing_eur_id: int,
        locking_strategy: str = "PESSIMISTIC",
    ) -> Transaction:
        """Inner implementation — separated so StaleDataError propagates."""
        send_amount = self._validate_send_amount(send_amount)
        locking_strategy = self._validate_locking_strategy(locking_strategy)

        rate_decimal, rate_text, normalized_rate = self._normalize_decimal_input(
            fx_rate,
            "fx_rate",
        )
        fingerprint = self._payment_fingerprint(
            payment_type="cross_currency",
            sender_id=sender_id,
            receiver_id=receiver_id,
            send_amount=send_amount,
            fx_rate=normalized_rate,
            fx_clearing_usd_id=fx_clearing_usd_id,
            fx_clearing_eur_id=fx_clearing_eur_id,
        )

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
                    return self._handle_existing_idempotency(session, existing, fingerprint)

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
                if fx_usd_acct.currency != sender_acct.currency:
                    raise ValueError(
                        "FX clearing account currency mismatch: source "
                        f"clearing account is {fx_usd_acct.currency}, "
                        f"sender account is {sender_acct.currency}."
                    )
                if fx_eur_acct.currency != receiver_acct.currency:
                    raise ValueError(
                        "FX clearing account currency mismatch: destination "
                        f"clearing account is {fx_eur_acct.currency}, "
                        f"receiver account is {receiver_acct.currency}."
                    )

                # ── Step 3: FX conversion (Decimal + explicit rounding) ──────
                recv_amount = self._convert_minor_units(
                    send_amount,
                    from_currency=sender_acct.currency,
                    to_currency=receiver_acct.currency,
                    rate=rate_decimal,
                )
                if recv_amount <= 0:
                    raise ValueError(
                        f"Converted receive amount must be positive, "
                        f"got {recv_amount} "
                        f"(send={send_amount}, rate={rate_text})."
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
                        f"{send_amount} minor units @ FX {rate_text}"
                    ),
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    transaction_type=TransactionType.PAYMENT,
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
                session.add(FxQuoteSnapshot(
                    transaction_id=txn.id,
                    from_currency=sender_acct.currency,
                    to_currency=receiver_acct.currency,
                    rate=rate_text,
                    rounding_mode=ROUNDING_MODE,
                    source_amount_minor=send_amount,
                    destination_amount_minor=recv_amount,
                ))
                session.flush()
                self._verify_transaction_balanced_by_currency(session, txn.id)

                # ── Step 7: OCC version touch ───────────────────────
                # For OCC, force a version_id bump on the Account rows.
                # If a concurrent txn already bumped the version,
                # session.flush() will raise StaleDataError.
                if locking_strategy == "OCC" and sender_acct and fx_eur_acct:
                    flag_modified(sender_acct, "name")
                    flag_modified(fx_eur_acct, "name")

                session.commit()
            except IntegrityError as exc:
                session.rollback()
                return self._recover_idempotent_integrity_error(
                    idempotency_key,
                    fingerprint,
                    exc,
                )
            except Exception:
                session.rollback()
                raise

        return self._load_transaction_by_key(idempotency_key)

    def execute_same_currency_payment(
        self,
        sender_id: int,
        receiver_id: int,
        send_amount: int,
        idempotency_key: str,
        *,
        locking_strategy: str = "PESSIMISTIC",
    ) -> Transaction:
        """Execute a two-leg transfer between accounts in the same currency."""
        try:
            return self._execute_same_currency_payment_inner(
                sender_id=sender_id,
                receiver_id=receiver_id,
                send_amount=send_amount,
                idempotency_key=idempotency_key,
                locking_strategy=locking_strategy,
            )
        except StaleDataError:
            raise ConcurrencyConflictError(
                "OCC conflict: Account version_id was modified by a "
                "concurrent transaction. Retry with a fresh read."
            )

    def _execute_same_currency_payment_inner(
        self,
        sender_id: int,
        receiver_id: int,
        send_amount: int,
        idempotency_key: str,
        *,
        locking_strategy: str = "PESSIMISTIC",
    ) -> Transaction:
        send_amount = self._validate_send_amount(send_amount)
        locking_strategy = self._validate_locking_strategy(locking_strategy)

        fingerprint = self._payment_fingerprint(
            payment_type="same_currency",
            sender_id=sender_id,
            receiver_id=receiver_id,
            send_amount=send_amount,
        )

        with self._session_factory() as session:
            try:
                if locking_strategy == "PESSIMISTIC":
                    session.connection(execution_options={"sqlite_begin_immediate": True})
                else:
                    session.begin()

                existing = (
                    session.query(Transaction)
                    .filter(Transaction.idempotency_key == idempotency_key)
                    .first()
                )
                if existing is not None:
                    return self._handle_existing_idempotency(session, existing, fingerprint)

                if locking_strategy == "PESSIMISTIC":
                    sender_acct = session.get(Account, sender_id, with_for_update=True)
                    receiver_acct = session.get(Account, receiver_id, with_for_update=True)
                else:
                    sender_acct = session.get(Account, sender_id)
                    receiver_acct = session.get(Account, receiver_id)

                if not sender_acct:
                    raise ValueError(f"Sender account {sender_id} does not exist.")
                if not receiver_acct:
                    raise ValueError(f"Receiver account {receiver_id} does not exist.")
                if sender_acct.currency != receiver_acct.currency:
                    raise ValueError(
                        "Same-currency payment requires sender and receiver "
                        "accounts to share a currency."
                    )

                sender_balance = self._get_account_balance(session, sender_id)
                if sender_balance < send_amount:
                    raise InsufficientFundsError(
                        f"Account {sender_id} has balance {sender_balance} "
                        f"minor units but tried to send {send_amount}."
                    )

                txn = Transaction(
                    description=(
                        f"Same-currency payment: Account {sender_id} → "
                        f"Account {receiver_id} | {send_amount} minor units"
                    ),
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    transaction_type=TransactionType.PAYMENT,
                )
                session.add(txn)
                session.flush()
                session.add_all([
                    Entry(
                        transaction_id=txn.id,
                        account_id=sender_id,
                        amount=send_amount,
                        direction=EntryDirection.CREDIT,
                    ),
                    Entry(
                        transaction_id=txn.id,
                        account_id=receiver_id,
                        amount=send_amount,
                        direction=EntryDirection.DEBIT,
                    ),
                ])
                session.flush()
                self._verify_transaction_balanced_by_currency(session, txn.id)

                if locking_strategy == "OCC" and sender_acct and receiver_acct:
                    flag_modified(sender_acct, "name")
                    flag_modified(receiver_acct, "name")

                session.commit()
            except IntegrityError as exc:
                session.rollback()
                return self._recover_idempotent_integrity_error(
                    idempotency_key,
                    fingerprint,
                    exc,
                )
            except Exception:
                session.rollback()
                raise

        return self._load_transaction_by_key(idempotency_key)

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
                    transaction_type=TransactionType.REVERSAL,
                    reversed_transaction_id=original.id,
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
                session.flush()
                self._verify_transaction_balanced_by_currency(session, rev_txn.id)

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
        Assert the accounting identity independently for each currency:

            For every currency:
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
        transaction_imbalances = self.get_transaction_currency_imbalances()
        if transaction_imbalances:
            details = ", ".join(
                f"txn {row['transaction_id']} {row['currency']}={row['net']}"
                for row in transaction_imbalances
            )
            raise InvariantViolationError(
                f"Transaction-level currency imbalances detected: {details}."
            )

        imbalances = {
            currency: net
            for currency, net in self.get_currency_invariant_balances().items()
            if net != 0
        }

        if imbalances:
            details = ", ".join(
                f"{currency}={net}" for currency, net in sorted(imbalances.items())
            )
            raise InvariantViolationError(
                f"Ledger imbalance detected by currency: {details}. "
                "Every currency must independently net to zero."
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
    append-only equity journal entries.

    No ``DELETE`` or destructive ``UPDATE`` statements are issued against
    ledger rows.  Seed funding flows through currency-specific System
    Equity accounts so USD and EUR balances cannot net against each other.

    Returns a dict mapping logical names to account IDs for convenience.

    Seed Data
    ---------
    1. User 1 (USD)  – funded with $100.00 (10 000 cents).
    2. User 2 (EUR)  – starts at €0.00.
    3. FX Clearing (USD) – pre-funded with $1 000 000.00 liquidity.
    4. FX Clearing (EUR) – pre-funded with €1 000 000.00 liquidity.
    5. System Equity (USD) – funding source for USD seed capital.
    6. System Equity (EUR) – funding source for EUR seed capital.

    The FX Clearing accounts simulate a corporate treasury pool that
    enables instant cross-currency settlement.
    """
    # Wipe and recreate schema (DDL — not row deletion). SQLite needs FK
    # checks disabled for self-referential/drop-order DDL, then re-enabled
    # before any seed data is inserted.
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF;")
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON;")

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
            equity_usd = Account(
                name="System Equity (USD)",
                currency="USD",
                type=AccountType.CORPORATE_FX_CLEARING,
            )
            equity_eur = Account(
                name="System Equity (EUR)",
                currency="EUR",
                type=AccountType.CORPORATE_FX_CLEARING,
            )
            session.add_all([user1, user2, fx_usd, fx_eur, equity_usd, equity_eur])
            session.flush()  # Materialize IDs

            # ── Seed funding transactions (append-only) ──────────────
            # All funding flows through currency-specific System Equity accounts.
            # Each transaction is a balanced pair of entries:
            #   DEBIT  recipient  (funds in)
            #   CREDIT equity     (funds out of same-currency equity pool)

            # Fund User 1 with $100.00
            fund_user1_txn = Transaction(
                description="Initial funding: Alice receives $100.00",
                idempotency_key="SEED_FUND_USER1",
                transaction_type=TransactionType.SEED,
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
                    account_id=equity_usd.id,
                    amount=10_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])
            LedgerEngine(session_factory)._verify_transaction_balanced_by_currency(
                session,
                fund_user1_txn.id,
            )

            # Capitalise FX Clearing USD pool — $1,000,000.00
            cap_usd_txn = Transaction(
                description="Treasury capitalisation: FX Clearing USD",
                idempotency_key="SEED_CAP_FX_USD",
                transaction_type=TransactionType.SEED,
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
                    account_id=equity_usd.id,
                    amount=100_000_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])
            LedgerEngine(session_factory)._verify_transaction_balanced_by_currency(
                session,
                cap_usd_txn.id,
            )

            # Capitalise FX Clearing EUR pool — €1,000,000.00
            cap_eur_txn = Transaction(
                description="Treasury capitalisation: FX Clearing EUR",
                idempotency_key="SEED_CAP_FX_EUR",
                transaction_type=TransactionType.SEED,
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
                    account_id=equity_eur.id,
                    amount=100_000_000,
                    direction=EntryDirection.CREDIT,
                ),
            ])
            LedgerEngine(session_factory)._verify_transaction_balanced_by_currency(
                session,
                cap_eur_txn.id,
            )

        # Return a map of logical names → account IDs
        return {  # type: ignore
            "user1": user1.id,
            "user2": user2.id,
            "fx_usd": fx_usd.id,
            "fx_eur": fx_eur.id,
            "equity_usd": equity_usd.id,
            "equity_eur": equity_eur.id,
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
    print(f"{BOLD}  DOUBLE-ENTRY PAYMENT LEDGER SIMULATOR{RESET}")
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
    FX_RATE_USD_TO_EUR = "0.92"  # 1 USD = 0.92 EUR
    SEND_AMOUNT = 5_000  # $50.00 in cents
    IDEM_KEY = "PAY-20260605-001"
    rate_decimal, _, _ = ledger._normalize_decimal_input(FX_RATE_USD_TO_EUR, "fx_rate")
    expected_receive = ledger._convert_minor_units(
        SEND_AMOUNT,
        from_currency="USD",
        to_currency="EUR",
        rate=rate_decimal,
    )

    print(f"  Sender  : Alice (User 1) — Account #{ids['user1']}")
    print(f"  Receiver: Bob   (User 2) — Account #{ids['user2']}")
    print(f"  Amount  : {_fmt_amount(SEND_AMOUNT, 'USD')}")
    print(f"  FX Rate : 1 USD = {FX_RATE_USD_TO_EUR} EUR")
    print(
        f"  Expected: Bob receives "
        f"{_fmt_amount(expected_receive, 'EUR')}"
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
        print(
            f"  {GREEN}✓ PASS: Ledger balances independently per currency "
            f"(Σ debits == Σ credits for each currency){RESET}"
        )
    except InvariantViolationError as e:
        print(f"  {RED}✗ FAIL: {e}{RESET}")
        sys.exit(1)

    try:
        ledger.verify_no_negative_user_balances()
        print(f"  {GREEN}✓ PASS: No user accounts are overdrawn.{RESET}")
    except InvariantViolationError as e:
        print(f"  {RED}✗ FAIL: {e}{RESET}")
        sys.exit(1)

    # ── 6. Idempotent retry attempt ─────────────────────────────────
    print_header("IDEMPOTENCY TEST — SAME-PAYLOAD RETRY")
    print(
        f"  {YELLOW}▸ Re-submitting payment with same idempotency key: "
        f"'{IDEM_KEY}'{RESET}"
    )

    try:
        retry_txn = ledger.execute_cross_currency_payment(
            sender_id=ids["user1"],
            receiver_id=ids["user2"],
            send_amount=SEND_AMOUNT,
            fx_rate=FX_RATE_USD_TO_EUR,
            idempotency_key=IDEM_KEY,  # ← same key!
            fx_clearing_usd_id=ids["fx_usd"],
            fx_clearing_eur_id=ids["fx_eur"],
        )
        if retry_txn.id != txn.id:
            print(f"  {RED}✗ FAIL: Retry returned a different transaction!{RESET}")
            sys.exit(1)
        print(
            f"  {GREEN}✓ PASS: Retry returned original transaction "
            f"#{txn.id} without double-posting.{RESET}"
        )
    except IdempotencyConflictError as e:
        print(f"  {RED}✗ FAIL: Same-payload retry conflicted: {e}{RESET}")
        sys.exit(1)

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
    print(f"{GREEN}{BOLD}  ALL SIMULATION CHECKS PASSED{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}\n")


if __name__ == "__main__":
    main()
