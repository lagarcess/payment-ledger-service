# Design

## Project Scope

This is an educational simulator, not production payment infrastructure. It is
designed to make double-entry ledger mechanics, FX clearing, idempotency,
reversals, and concurrency tradeoffs visible in a small FastAPI/SQLite app.

## Accounting Convention

The current convention is:

- `DEBIT` increases an account balance.
- `CREDIT` decreases an account balance.

Example same-currency transfer:

```text
sender      CREDIT  1000
recipient   DEBIT   1000
```

Example USD to EUR cross-currency transfer:

```text
sender                 CREDIT  send_amount_usd
FX_CLEARING_USD        DEBIT   send_amount_usd

FX_CLEARING_EUR        CREDIT  receive_amount_eur
recipient              DEBIT   receive_amount_eur
```

## Data Model

- `Account`: single-currency account with a type (`USER` or `CORPORATE_FX_CLEARING`) and `version_id` for the OCC demo.
- `Transaction`: append-only journal header with timestamp, idempotency key, request fingerprint, transaction type, and optional reversal pointer.
- `Entry`: immutable debit/credit leg with a positive integer minor-unit amount.
- `FxQuoteSnapshot`: audit metadata for a cross-currency transaction, including rate, currencies, source/destination minor amounts, timestamp, and rounding mode.

## Balance Derivation

Balances are derived from immutable entries with aggregate queries. The app does
not maintain a stored balance column or cache table.

```text
balance = SUM(DEBIT amounts) - SUM(CREDIT amounts)
```

## Currency-Aware Invariants

The ledger balances per currency, not globally across currencies. A USD debit
must be matched by USD credit, and an EUR debit must be matched by EUR credit.
The invariant query joins `entries` to `accounts` and groups by
`Account.currency`.

## Cross-Currency Payments

Cross-currency payments route through currency-specific clearing accounts. The
source-currency side and destination-currency side are independently balanced.
The destination clearing account must have enough liquidity to fund the
recipient.

## Exchange Rates and Rounding

Rates are supplied as snapshots by the caller. The simulator does not fetch live
exchange rates. Core conversion rejects Python `float`, uses `Decimal`, and
quantizes with `ROUND_HALF_UP` to the destination currency precision before
posting integer minor units.

## Idempotency

Each payment uses a unique `idempotency_key`. The ledger stores a normalized
request fingerprint:

- Same key plus same fingerprint returns the original transaction.
- Same key plus different fingerprint raises an idempotency conflict.
- Database unique-constraint conflicts are mapped back to retry/conflict
  behavior when possible.

## Fees

Fees are not implemented in the current API. A planned sender-paid fee model
would post:

```text
sender                 CREDIT  gross_send_amount_usd
PLATFORM_FEES_USD      DEBIT   fee_amount_usd
FX_CLEARING_USD        DEBIT   net_fx_amount_usd

FX_CLEARING_EUR        CREDIT  receive_amount_eur
recipient              DEBIT   receive_amount_eur
```

## Reversals

Corrections use compensating transactions, not deletes. A reversal transaction
sets `transaction_type = REVERSAL`, points at the original transaction, and
creates flipped entry directions.

## Concurrency

The app demonstrates two concurrency ideas:

- SQLite pessimistic demo path with `BEGIN IMMEDIATE`.
- SQLAlchemy optimistic version-counter path using an account version touch.

These mechanisms are useful for teaching race conditions. They are not a full
production concurrency design.

## Known Limitations

- SQLite/demo scope.
- Not production-ready.
- Limited currencies (`USD`, `EUR` in the seed data).
- Single-currency accounts; true multi-currency balances would need currency on
  entries or a separate account-balance dimension.
- No real FX provider.
- No distributed idempotency system.
- No durable migration strategy beyond SQLAlchemy create/drop for the demo.
- No full reconciliation pipeline.
- No authentication or authorization boundaries.
- No fee posting in the current API.

## What I’d Do With More Time

- Add durable account and migration tooling.
- Add true multi-currency account balances if the product goal required them.
- Move every public payment API toward integer minor units only.
- Strengthen the quote model with provider, quote expiry, quote signatures, and
  quote/replay rules.
- Use database-native row-level locking or clearer OCC with retries on a
  production database.
- Add reconciliation jobs and property-based invariant tests.
- Add monitoring, alerts, structured audit logs, and operational runbooks.
- Add authentication, authorization, account ownership, and admin boundaries.
