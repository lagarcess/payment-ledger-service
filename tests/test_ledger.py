from decimal import Decimal

import pytest
import concurrent.futures
from unittest import mock

from src.models import (
    Account,
    AccountType,
    Entry,
    FxQuoteSnapshot,
    Transaction,
    EntryDirection,
)
from src.ledger import (
    InsufficientFundsError,
    ConcurrencyConflictError,
    IdempotencyConflictError,
    InvariantViolationError,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# A. Mathematical Invariants & Math
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_cross_currency_success(seeded_db):
    """Execute a valid USD to EUR payment and assert success invariants."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    # Initial balance User 1: $100 (10000 cents)
    send_amount = 5000  # $50.00
    fx_rate = "0.92"
    
    txn = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=send_amount,
        fx_rate=fx_rate,
        idempotency_key="TEST-PAY-001",
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"]
    )
    
    # Assert exactly 4 Entry legs were created for this transaction
    with session_factory() as session:
        entries = session.query(Entry).filter_by(transaction_id=txn.id).all()
        assert len(entries) == 4

        per_currency = {}
        for entry in entries:
            signed_amount = entry.amount if entry.direction == EntryDirection.DEBIT else -entry.amount
            per_currency[entry.account.currency] = (
                per_currency.get(entry.account.currency, 0) + signed_amount
            )

        assert per_currency == {"USD": 0, "EUR": 0}
        
    # Assert the system invariants hold
    assert ledger.verify_system_invariants() is True
    assert ledger.verify_no_negative_user_balances() is True


def test_seeded_ledger_balances_independently_by_currency(seeded_db):
    """Bootstrap funding must not rely on a MULTI account to hide currency nets."""
    ledger = seeded_db["ledger"]
    session_factory = seeded_db["session_factory"]

    assert ledger.verify_system_invariants() is True

    with session_factory() as session:
        currencies = {
            currency
            for (currency,) in session.query(Account.currency).distinct().all()
        }

    assert "MULTI" not in currencies
    assert {"USD", "EUR"}.issubset(currencies)


def test_system_invariant_rejects_cross_currency_netting(seeded_db):
    """An opposite USD/EUR imbalance must not pass as a globally net-zero ledger."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    with session_factory() as session:
        with session.begin():
            txn = Transaction(
                description="Deliberately invalid mixed-currency imbalance",
                idempotency_key="TEST-MIXED-CURRENCY-IMBALANCE",
            )
            session.add(txn)
            session.flush()
            session.add_all([
                Entry(
                    transaction_id=txn.id,
                    account_id=account_ids["user1"],
                    amount=1234,
                    direction=EntryDirection.DEBIT,
                ),
                Entry(
                    transaction_id=txn.id,
                    account_id=account_ids["fx_eur"],
                    amount=1234,
                    direction=EntryDirection.CREDIT,
                ),
            ])

    with pytest.raises(InvariantViolationError, match="USD|EUR"):
        ledger.verify_system_invariants()


def test_cross_currency_payment_records_decimal_fx_snapshot(seeded_db):
    """FX conversion uses a supplied Decimal/string rate and records the snapshot."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    txn = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=1001,
        fx_rate="0.925",
        idempotency_key="TEST-FX-SNAPSHOT",
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"],
    )

    with session_factory() as session:
        snapshot = (
            session.query(FxQuoteSnapshot)
            .filter(FxQuoteSnapshot.transaction_id == txn.id)
            .one()
        )

    assert snapshot.from_currency == "USD"
    assert snapshot.to_currency == "EUR"
    assert snapshot.rate == "0.925"
    assert snapshot.rounding_mode == "ROUND_HALF_UP"
    assert snapshot.source_amount_minor == 1001
    assert snapshot.destination_amount_minor == 926


def test_core_fx_rate_rejects_float_inputs(seeded_db):
    """The ledger core should not accept binary floating-point FX rates."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    with pytest.raises(ValueError, match="fx_rate.*string"):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1000,
            fx_rate=0.92,
            idempotency_key="TEST-FLOAT-FX-REJECTED",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
        )


def test_same_currency_transfer_creates_two_balanced_entries(seeded_db):
    """Same-currency payments should not route through FX clearing accounts."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    with session_factory() as session:
        with session.begin():
            charlie = Account(
                name="Charlie (User 3)",
                currency="USD",
                type=AccountType.USER,
            )
            session.add(charlie)
            session.flush()
            charlie_id = charlie.id

    txn = ledger.execute_same_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=charlie_id,
        send_amount=2500,
        idempotency_key="TEST-SAME-CURRENCY",
    )

    with session_factory() as session:
        entries = session.query(Entry).filter_by(transaction_id=txn.id).all()

    assert len(entries) == 2
    assert ledger.get_account_balance(account_ids["user1"]) == 7500
    assert ledger.get_account_balance(charlie_id) == 2500
    assert ledger.verify_system_invariants() is True


def test_overdraft_protection(seeded_db):
    """Attempt to send more money than the sender has; should fail cleanly."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    # User 1 has $100. Try sending $200.
    send_amount = 20000  # $200.00
    idem_key = "TEST-PAY-OVERDRAFT"

    with pytest.raises(InsufficientFundsError):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=send_amount,
            fx_rate="0.92",
            idempotency_key=idem_key,
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"]
        )

    # Assert NO entries or transactions were created
    with session_factory() as session:
        txn = session.query(Transaction).filter_by(idempotency_key=idem_key).first()
        assert txn is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# B. Immutability & Reversals
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_idempotency_guard(seeded_db):
    """Execute the exact same payment payload twice; should return original."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    idem_key = "TEST-PAY-IDEMPOTENCY"

    # First attempt - succeeds
    first = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=1000,
        fx_rate="0.92",
        idempotency_key=idem_key,
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"]
    )

    # Second attempt with same idempotency key and payload is idempotent.
    second = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=1000,
        fx_rate="0.92",
        idempotency_key=idem_key,
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"]
    )

    assert second.id == first.id


def test_transaction_reversal(seeded_db):
    """Execute a payment, then reverse it and verify append-only integrity."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    initial_balance = ledger.get_account_balance(account_ids["user1"])
    assert initial_balance == 10000  # $100.00

    # Execute payment
    txn = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=5000,
        fx_rate="0.92",
        idempotency_key="TEST-PAY-REVERSAL",
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"]
    )

    assert ledger.get_account_balance(account_ids["user1"]) == 5000

    with session_factory() as session:
        initial_txn_count = session.query(Transaction).count()
        initial_entry_count = session.query(Entry).count()

    # Reverse transaction
    ledger.reverse_transaction(txn.id)

    # Assert balance returned to initial state
    assert ledger.get_account_balance(account_ids["user1"]) == initial_balance

    # Assert invariant is still true
    assert ledger.verify_system_invariants() is True

    # Assert no rows were deleted (append-only)
    with session_factory() as session:
        assert session.query(Transaction).count() == initial_txn_count + 1
        assert session.query(Entry).count() == initial_entry_count + 4


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# C. Concurrency & Race Conditions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_occ_conflict(seeded_db):
    """Simulate a background modification and attempt to commit an OCC payment."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    original_get_balance = ledger._get_account_balance

    def fake_get_balance(session, account_id):
        """
        Intercept the balance check (which occurs after OCC reads but before OCC commit)
        to alter the version_id in the background, simulating a race condition.
        """
        if account_id == account_ids["user1"]:
            with session_factory() as bg_session:
                acct = bg_session.get(Account, account_id)
                # Modifying name triggers version_id bump on commit
                acct.name = acct.name + " updated"
                bg_session.commit()
        return original_get_balance(session, account_id)

    # Patch the _get_account_balance to inject our concurrent update
    with mock.patch.object(ledger, '_get_account_balance', side_effect=fake_get_balance):
        with pytest.raises(ConcurrencyConflictError):
            ledger.execute_cross_currency_payment(
                sender_id=account_ids["user1"],
                receiver_id=account_ids["user2"],
                send_amount=1000,
                fx_rate="0.92",
                idempotency_key="TEST-PAY-OCC-CONFLICT",
                fx_clearing_usd_id=account_ids["fx_usd"],
                fx_clearing_eur_id=account_ids["fx_eur"],
                locking_strategy="OCC"  # Force OCC strategy
            )


def test_pessimistic_race_condition(seeded_db):
    """Use ThreadPoolExecutor to fire two simultaneous threads draining the same balance."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    
    assert ledger.get_account_balance(account_ids["user1"]) == 10000

    def drain_account(idem_key):
        return ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=10000,  # Drain exactly the entire balance
            fx_rate="0.92",
            idempotency_key=idem_key,
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
            locking_strategy="PESSIMISTIC"
        )

    results = []
    exceptions = []

    # Fire two threads concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(drain_account, "TEST-RACE-1"),
            executor.submit(drain_account, "TEST-RACE-2")
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                exceptions.append(e)

    # Exactly one thread succeeds
    assert len(results) == 1
    # Exactly one thread fails with InsufficientFundsError
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], InsufficientFundsError)

    # Final balance safely 0
    assert ledger.get_account_balance(account_ids["user1"]) == 0
    assert ledger.verify_system_invariants() is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# D. System Boundaries & Routing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_precision_scale_limits(seeded_db):
    """Verify BigInteger columns handle massive scale without overflowing."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    # 900 trillion cents
    massive_amount = 900_000_000_000_000

    # Seed the massive amount into sender's account using an equity journal
    with session_factory() as session:
        with session.begin():
            txn = Transaction(
                description="Massive funding for scale test",
                idempotency_key="TEST-MASSIVE-FUNDING"
            )
            session.add(txn)
            session.flush()
            session.add_all([
                Entry(
                    transaction_id=txn.id,
                    account_id=account_ids["user1"],
                    amount=massive_amount,
                    direction=EntryDirection.DEBIT
                ),
                Entry(
                    transaction_id=txn.id,
                    account_id=account_ids["fx_eur"],
                    amount=massive_amount,  # Sufficient to cover 0.92 conversion
                    direction=EntryDirection.DEBIT
                ),
                Entry(
                    transaction_id=txn.id,
                    account_id=account_ids["equity_usd"],
                    amount=massive_amount,
                    direction=EntryDirection.CREDIT
                ),
                Entry(
                    transaction_id=txn.id,
                    account_id=account_ids["equity_eur"],
                    amount=massive_amount,
                    direction=EntryDirection.CREDIT
                )
            ])

    # Execute a cross-currency payment for that massive amount
    txn = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=massive_amount,
        fx_rate="0.92",
        idempotency_key="TEST-MASSIVE-PAYMENT",
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"]
    )
    
    # Assert success and invariants held
    assert txn is not None
    assert ledger.verify_system_invariants() is True


def test_invalid_currency_routing(seeded_db):
    """Attempt cross-currency payment with unsupported currency."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]
    
    # Simulate a missing Corporate FX pool for 'JPY'
    # By passing a non-existent account ID, the ledger will find a zero balance
    # and raise InsufficientFundsError
    fake_fx_clearing_jpy_id = 99999

    with session_factory() as session:
        initial_entry_count = session.query(Entry).count()

    with pytest.raises(ValueError):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1000,
            fx_rate="150.0",  # USD to JPY fake rate
            idempotency_key="TEST-INVALID-CURRENCY",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=fake_fx_clearing_jpy_id
        )

    # Assert NO orphaned entry legs were created
    with session_factory() as session:
        assert session.query(Entry).count() == initial_entry_count


def test_fx_clearing_currency_mismatch_is_rejected_cleanly(seeded_db):
    """FX clearing accounts must match the source and destination currencies."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    with pytest.raises(ValueError, match="FX clearing.*currency"):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1000,
            fx_rate="0.92",
            idempotency_key="TEST-FX-CURRENCY-MISMATCH",
            fx_clearing_usd_id=account_ids["fx_eur"],
            fx_clearing_eur_id=account_ids["fx_usd"],
        )


def test_same_idempotency_key_retry_returns_original_transaction(seeded_db):
    """A same-payload retry should not create a second transaction."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    kwargs = dict(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=1000,
        fx_rate="0.92",
        idempotency_key="TEST-IDEMPOTENT-RETRY",
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"],
    )

    first = ledger.execute_cross_currency_payment(**kwargs)
    second = ledger.execute_cross_currency_payment(**kwargs)

    assert second.id == first.id
    with session_factory() as session:
        assert (
            session.query(Transaction)
            .filter(Transaction.idempotency_key == "TEST-IDEMPOTENT-RETRY")
            .count()
        ) == 1
        assert session.query(Entry).filter_by(transaction_id=first.id).count() == 4


def test_same_idempotency_key_with_different_payload_is_rejected(seeded_db):
    """A reused key with a different fingerprint should be a conflict."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=1000,
        fx_rate="0.92",
        idempotency_key="TEST-IDEMPOTENCY-CONFLICT",
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"],
    )

    with pytest.raises(IdempotencyConflictError):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1001,
            fx_rate="0.92",
            idempotency_key="TEST-IDEMPOTENCY-CONFLICT",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
        )


def test_concurrent_same_key_requests_do_not_double_post(seeded_db):
    """Duplicate concurrent retries should converge on one transaction."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    def submit_payment():
        return ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1000,
            fx_rate="0.92",
            idempotency_key="TEST-CONCURRENT-IDEMPOTENCY",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
            locking_strategy="PESSIMISTIC",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: submit_payment(), range(2)))

    assert {txn.id for txn in results} == {results[0].id}
    with session_factory() as session:
        assert (
            session.query(Transaction)
            .filter(Transaction.idempotency_key == "TEST-CONCURRENT-IDEMPOTENCY")
            .count()
        ) == 1


def test_invalid_amount_is_rejected(seeded_db):
    """Payment amounts must be positive integer minor units."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    with pytest.raises(ValueError, match="positive"):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=0,
            fx_rate="0.92",
            idempotency_key="TEST-ZERO-AMOUNT",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
        )


@pytest.mark.parametrize("bad_amount", [1000.5, Decimal("1000"), "1000", True])
def test_cross_currency_payment_rejects_non_integer_minor_units(seeded_db, bad_amount):
    """Posted ledger amounts must be exact Python ints, not numeric lookalikes."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    with pytest.raises(ValueError, match="integer minor-unit"):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=bad_amount,
            fx_rate="0.92",
            idempotency_key=f"TEST-BAD-AMOUNT-{type(bad_amount).__name__}",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
        )


def test_same_currency_payment_rejects_non_integer_minor_units(seeded_db):
    """The two-leg path enforces the same integer amount rule."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    with session_factory() as session:
        with session.begin():
            charlie = Account(
                name="Charlie (User 3)",
                currency="USD",
                type=AccountType.USER,
            )
            session.add(charlie)
            session.flush()
            charlie_id = charlie.id

    with pytest.raises(ValueError, match="integer minor-unit"):
        ledger.execute_same_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=charlie_id,
            send_amount=1000.5,
            idempotency_key="TEST-SAME-BAD-AMOUNT",
        )


def test_invalid_locking_strategy_is_rejected(seeded_db):
    """A typo should not silently disable both locking modes."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    with pytest.raises(ValueError, match="locking_strategy"):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1000,
            fx_rate="0.92",
            idempotency_key="TEST-BAD-LOCK",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
            locking_strategy="TYPO",
        )


def test_system_invariant_detects_offsetting_bad_transactions(seeded_db):
    """System verification must scan transaction-level currency balance too."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]
    session_factory = seeded_db["session_factory"]

    with session_factory() as session:
        with session.begin():
            debit_only = Transaction(
                description="Invalid USD debit-only transaction",
                idempotency_key="TEST-BAD-TXN-DEBIT",
            )
            credit_only = Transaction(
                description="Invalid USD credit-only transaction",
                idempotency_key="TEST-BAD-TXN-CREDIT",
            )
            session.add_all([debit_only, credit_only])
            session.flush()
            session.add_all([
                Entry(
                    transaction_id=debit_only.id,
                    account_id=account_ids["user1"],
                    amount=777,
                    direction=EntryDirection.DEBIT,
                ),
                Entry(
                    transaction_id=credit_only.id,
                    account_id=account_ids["fx_usd"],
                    amount=777,
                    direction=EntryDirection.CREDIT,
                ),
            ])

    with pytest.raises(InvariantViolationError, match="Transaction-level"):
        ledger.verify_system_invariants()


def test_fx_clearing_liquidity_is_enforced(seeded_db):
    """The receiver-currency clearing pool must have enough liquidity."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    with pytest.raises(InsufficientFundsError, match="FX Clearing"):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=10_000,
            fx_rate="20000",
            idempotency_key="TEST-FX-LIQUIDITY",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"],
        )


def test_decimal_rate_object_is_accepted_without_float_math(seeded_db):
    """Callers that already parsed Decimal rates can pass them directly."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    txn = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=1000,
        fx_rate=Decimal("0.92"),
        idempotency_key="TEST-DECIMAL-FX",
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"],
    )

    assert txn is not None
