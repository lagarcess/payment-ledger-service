import pytest
import concurrent.futures
from unittest import mock

from src.models import Account, Entry, Transaction, EntryDirection
from src.ledger import (
    InsufficientFundsError,
    DuplicateTransactionError,
    ConcurrencyConflictError
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
    fx_rate = 0.92
    
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
        
    # Assert the system invariants hold
    assert ledger.verify_system_invariants() is True
    assert ledger.verify_no_negative_user_balances() is True


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
            fx_rate=0.92,
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
    """Execute the exact same payment payload twice; should block second attempt."""
    ledger = seeded_db["ledger"]
    account_ids = seeded_db["account_ids"]

    idem_key = "TEST-PAY-IDEMPOTENCY"

    # First attempt - succeeds
    ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=1000,
        fx_rate=0.92,
        idempotency_key=idem_key,
        fx_clearing_usd_id=account_ids["fx_usd"],
        fx_clearing_eur_id=account_ids["fx_eur"]
    )

    # Second attempt with same idempotency key - fails
    with pytest.raises(DuplicateTransactionError):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1000,
            fx_rate=0.92,
            idempotency_key=idem_key,
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=account_ids["fx_eur"]
        )


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
        fx_rate=0.92,
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
                fx_rate=0.92,
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
            fx_rate=0.92,
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
                    account_id=account_ids["equity"],
                    amount=massive_amount * 2,
                    direction=EntryDirection.CREDIT
                )
            ])

    # Execute a cross-currency payment for that massive amount
    txn = ledger.execute_cross_currency_payment(
        sender_id=account_ids["user1"],
        receiver_id=account_ids["user2"],
        send_amount=massive_amount,
        fx_rate=0.92,
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

    with pytest.raises(InsufficientFundsError):
        ledger.execute_cross_currency_payment(
            sender_id=account_ids["user1"],
            receiver_id=account_ids["user2"],
            send_amount=1000,
            fx_rate=150.0,  # USD to JPY fake rate
            idempotency_key="TEST-INVALID-CURRENCY",
            fx_clearing_usd_id=account_ids["fx_usd"],
            fx_clearing_eur_id=fake_fx_clearing_jpy_id
        )

    # Assert NO orphaned entry legs were created
    with session_factory() as session:
        assert session.query(Entry).count() == initial_entry_count
