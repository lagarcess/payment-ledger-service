# Product Design

## Purpose

This document describes the user-facing dashboard experience for the educational
multi-currency ledger simulator. It covers visual design, interaction patterns,
component behavior, and copy tone.

It does not define accounting behavior or backend safety rules. For those, see
[../engineering-design/DESIGN.md](../engineering-design/DESIGN.md).

## Product Scope

The interface is a learning console for exploring:

- double-entry ledger entries
- cross-currency FX clearing
- currency-aware invariant checks
- idempotency behavior
- reversals
- SQLite concurrency tradeoffs

The UI should feel precise and credible, but it must not imply that the project
is production payment infrastructure.

## Copy Principles

Use neutral, demonstrable language:

- "Educational ledger simulator"
- "Learning console"
- "Concept demo"
- "Currency-aware invariant"
- "FX clearing flow"
- "SQLite concurrency demo"

Avoid unsupported claims:

- customer counts or adoption numbers
- banking, compliance, or production-readiness claims
- copy that implies regulated payment processing
- marketing statements that describe scale the project does not have

Good example headings:

- "Ledger Simulator"
- "Read the ledger in four moves"
- "Inspect the FX clearing legs"
- "Verify currency-aware balance"
- "Simulate a concurrency race"

Avoid headings that:

- imply banking or regulated payment capability
- claim customer counts, adoption, or scale
- promote subscriptions or plans that do not exist in the simulator
- describe the demo as production infrastructure

## Experience Model

The dashboard has two primary work zones:

- A left-side payment terminal for configuring and executing simulator actions.
- A main ledger workspace for reading state, invariants, accounts, transactions,
  and entry legs.

The first screen should make the simulator usable immediately. Do not replace
the dashboard with a marketing landing page. If explanatory content is added,
keep it close to the controls and state it helps interpret.

## Visual Language

The current interface uses a restrained fintech-inspired palette:

| Token | Light | Dark | Use |
|---|---:|---:|---|
| Canvas | `#ffffff` | `#000000` | Page background |
| Surface | `#f4f4f4` | `#16181a` | Panels and quiet groups |
| Text | `#191c1f` | `#ffffff` | Primary readable text |
| Muted text | `#505a63` | `rgba(255,255,255,0.55)` | Helper text and captions |
| Primary | `#494fdf` | `#4f55f1` | Focus, actions, key accents |
| Success | `#00a87e` | `#00a87e` | Debits, healthy state, positive markers |
| Danger | `#e23b4a` | `#e23b4a` | Credits, imbalance, error states |
| Warning | `#ec7e00` | `#ec7e00` | Pending/wake/race-state feedback |

Use accent color to explain state, not to decorate every surface. The interface
should remain readable and operational.

## Typography

The dashboard uses:

- `Inter Tight` for display headings.
- `Inter` for body text, controls, tables, and metadata.

Guidelines:

- Keep dashboard headings compact and functional.
- Use uppercase micro-labels sparingly for section labels and metadata.
- Avoid oversized marketing-style type inside operational panels.
- Keep button and table text readable at mobile widths.

## Layout

The desktop layout is a persistent terminal plus a scrollable workspace:

- Sidebar: payment parameters, idempotency controls, locking mode, primary
  actions, and backend settings access.
- Main workspace: title, quick guide, invariant status, metrics, account table,
  transaction journal, and ledger entry legs.

Layout principles:

- The payment terminal should stay scannable and predictable.
- The invariant and metrics should remain near the top of the reading flow.
- Tables should favor dense but readable rows over decorative cards.
- Repeated records can be table rows or compact cards; avoid nested cards.

## Core Components

### Payment Terminal

The terminal is a control surface, not a promotional panel. It should make
inputs obvious and keep simulator mechanics visible:

- sender and receiver selectors
- source amount input
- FX rate slider or input
- idempotency key controls
- locking strategy selector
- execute, race simulation, and reset actions

### Quick Guide

The quick guide explains the demo workflow in compact steps:

1. Connect
2. Transfer
3. Verify
4. Stress

Keep these labels short and action-oriented. The copy should help a learner
interpret the dashboard without claiming real-world payment readiness.

### Invariant Card

The invariant card is the most important correctness signal. It should clearly
distinguish:

- balanced per-currency state
- detected per-currency imbalance
- protected/offline backend state
- remote backend wake state

Do not describe a global-only check as sufficient for multi-currency accounting.

### Metrics

Metrics should summarize simulator state:

- debit and credit totals
- transaction count
- entry count
- account count
- user transaction count

Avoid business metrics such as revenue, customers, users, or payment volume
unless the app actually computes them as simulator state.

### Tables

Tables should preserve accounting clarity:

- Accounts show account name, type, currency, and derived balance.
- Transactions show idempotency key, description, and entry count.
- Entry legs show transaction, account, currency, direction, and amount.

Use color consistently:

- `DEBIT` in success/teal
- `CREDIT` in danger/red
- imbalance/error state in danger/red
- pending/wake state in warning/orange

### Toasts

Toasts should confirm simulator outcomes or explain failures. They should be
visible outside the sidebar stack, readable on mobile, and dismissible.

## Interaction Principles

- Preserve the default sample flow so a new visitor can execute a payment
  without setup.
- Keep backend controls available from the gear menu without blocking the main
  dashboard.
- Prefer clear error messages over generic server failures.
- After an action, refresh state and make the new ledger rows easy to find.
- Treat destructive demo actions like reset as explicit commands with clear
  labeling.

## Responsive Behavior

Desktop:

- Sidebar and workspace appear side by side.
- Tables can use full column sets.
- Quick guide cards can display in a four-column grid.

Tablet:

- Reduce spacing before hiding important data.
- Allow guide cards and tables to wrap or scroll horizontally.

Mobile:

- Stack the terminal and workspace vertically.
- Keep touch targets at least 44px tall where practical.
- Keep toasts within viewport bounds.
- Prefer horizontal table scrolling to dropping accounting columns.

## Accessibility

- Keep text contrast high in both light and dark modes.
- Controls need visible focus states.
- Icon-only controls need labels or titles.
- Toasts should use status/alert semantics.
- Do not rely on color alone to communicate debit, credit, success, warning, or
  failure.

## Known Product Design Limits

- This document describes the current dashboard, not a public marketing site.
- It does not define authenticated account-management flows.
- It does not define mobile app screenshots, app-store surfaces, subscription
  pages, or customer-scale claims.
- It does not replace the engineering design doc for ledger correctness.

## What I Would Refine With More Time

- Add a dedicated transaction detail drawer for audit metadata and FX snapshots.
- Add clearer empty, loading, wake, and protected-backend states.
- Add a visual diff between original and reversal transactions.
- Improve responsive table affordances for narrow screens.
- Add visual regression checks for the dashboard.
