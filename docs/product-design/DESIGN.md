---
version: alpha
name: product-design
description: |
  Product design guidance for the current Ledger Simulator dashboard. The UI is
  a focused educational console, not a promotional page: a sticky payment terminal
  sits beside ledger inspection surfaces for invariants, FX flow, accounts,
  transactions, entries, settings, and operational feedback. The visual system
  should feel precise, inspectable, and calm without implying real-world payment
  capability.

colors:
  canvas:
    light: "#ffffff"
    dark: "#000000"
  surface:
    light: "#f4f4f4"
    dark: "#16181a"
  input:
    light: "#ffffff"
    dark: "#0a0a0a"
  border:
    light: "#e2e2e7"
    dark: "rgba(255,255,255,0.12)"
  sidebar-border:
    light: "#e2e2e7"
    dark: "rgba(255,255,255,0.08)"
  text:
    light: "#191c1f"
    dark: "#ffffff"
  text-muted:
    light: "#505a63"
    dark: "rgba(255,255,255,0.55)"
  primary: "#494fdf"
  primary-dark-mode: "#4f55f1"
  primary-hover-light: "#3a40c9"
  primary-hover-dark: "#6368f3"
  success: "#00a87e"
  success-bg-light: "rgba(0,168,126,0.10)"
  success-bg-dark: "rgba(0,168,126,0.15)"
  danger: "#e23b4a"
  danger-bg-light: "rgba(226,59,74,0.10)"
  danger-bg-dark: "rgba(226,59,74,0.20)"
  warning: "#ec7e00"
  warning-strong: "#d97706"
  warning-bg-light: "rgba(236,126,0,0.10)"
  warning-bg-dark: "rgba(236,126,0,0.18)"

typography:
  family-body: "Inter, system-ui, sans-serif"
  family-display: "Inter Tight, Inter, sans-serif"
  family-mono: "ui-monospace, SF Mono, Menlo, monospace"
  page-title:
    fontFamily: "{typography.family-display}"
    fontSize: 42px
    fontWeight: 500
    lineHeight: 1.0
    letterSpacing: -0.6px
  page-title-tablet:
    fontSize: 36px
  page-title-mobile:
    fontSize: 32px
  section-title:
    fontFamily: "{typography.family-display}"
    fontSize: 22px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: -0.2px
  guide-title:
    fontFamily: "{typography.family-display}"
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.15
  sidebar-title:
    fontFamily: "{typography.family-display}"
    fontSize: 20px
    fontWeight: 500
    lineHeight: 1.2
  card-title:
    fontFamily: "{typography.family-display}"
    fontSize: 17px
    fontWeight: 600
    lineHeight: 1.2
  metric-value:
    fontFamily: "{typography.family-display}"
    fontSize: 32px
    fontWeight: 600
    letterSpacing: -0.5px
  metric-value-mobile:
    fontSize: 26px
  body:
    fontFamily: "{typography.family-body}"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "{typography.family-body}"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.45
  helper:
    fontFamily: "{typography.family-body}"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "{typography.family-body}"
    fontSize: 11px
    fontWeight: 600
    letterSpacing: 1.2px
    textTransform: uppercase
  table:
    fontFamily: "{typography.family-body}"
    fontSize: 14px
  mono:
    fontFamily: "{typography.family-mono}"
    fontSize: 13px
    lineHeight: 2.0

rounded:
  tiny: 4px
  sm: 6px
  md: 8px
  input: 10px
  table: 12px
  toast: 14px
  card: 20px
  pill: 9999px

spacing:
  xxs: 2px
  xs: 4px
  sm: 6px
  md: 8px
  lg: 10px
  xl: 12px
  xxl: 16px
  card: 18px
  panel: 22px
  sidebar-x: 24px
  sidebar-y: 32px
  main: 40px

layout:
  sidebar-width: 320px
  main-max-width: 1100px
  desktop-viewport: ">= 901px"
  stacked-breakpoint: "max-width: 900px"
  compact-breakpoint: "max-width: 560px"

components:
  app-shell:
    desktop: "flex row, min-height 100vh"
    tablet-mobile: "flex column"
  sidebar:
    width: "{layout.sidebar-width}"
    backgroundColor: "{colors.canvas}"
    border: "right hairline on desktop, bottom hairline when stacked"
    paddingDesktop: "32px 24px"
    paddingTablet: "24px"
    paddingMobile: "22px 18px"
    behavior: "sticky full-height terminal on desktop; normal document flow on smaller screens"
  main-content:
    maxWidth: "{layout.main-max-width}"
    paddingDesktop: "40px"
    paddingTablet: "32px 24px"
    paddingMobile: "28px 18px"
  button-primary:
    backgroundColor: "{colors.text}"
    textColor: "{colors.canvas}"
    fontSize: 15px
    fontWeight: 600
    rounded: "{rounded.pill}"
    height: 46px
  button-secondary:
    backgroundColor: transparent
    textColor: "{colors.text}"
    border: "{colors.border}"
    fontSize: 14px
    fontWeight: 500
    rounded: "{rounded.pill}"
    height: 42px
  button-warning:
    backgroundColor: transparent
    textColor: "{colors.warning-strong}"
    border: "rgba(217,119,6,0.30)"
    fontSize: 13px
    fontWeight: 500
    rounded: "{rounded.pill}"
    height: 42px
  form-control:
    backgroundColor: "{colors.input}"
    border: "{colors.border}"
    rounded: "{rounded.input}"
    padding: "10px 12px"
    fontSize: 14px
  settings-popover:
    backgroundColor: "{colors.canvas}"
    border: "{colors.border}"
    rounded: "{rounded.table}"
    width: "min(340px, calc(100vw - 48px))"
  quick-guide-card:
    backgroundColor: "{colors.canvas}"
    border: "{colors.border}"
    rounded: "{rounded.md}"
    padding: 16px
    accentBar: "3px top border in primary, success, danger, or warning"
  invariant-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    paddingDesktop: "22px 28px"
    paddingMobile: "18px"
  metric-card:
    layout: "label over large value, no decorative card chrome"
  flow-card:
    backgroundColor: "{colors.surface}"
    border: "{colors.border}"
    rounded: "{rounded.card}"
    paddingDesktop: "24px 28px"
    paddingMobile: "20px"
    fontFamily: "{typography.family-mono}"
    overflowX: auto
  table-container:
    backgroundColor: "{colors.surface}"
    border: "{colors.border}"
    rounded: "{rounded.table}"
    overflow: hidden
  tabs-list:
    backgroundColor: "{colors.surface}"
    border: "{colors.border}"
    rounded: "{rounded.pill}"
    padding: 4px
  toast:
    width: "min(420px, calc(100vw - 48px))"
    minHeight: 64px
    rounded: "{rounded.toast}"
    placementDesktop: "top right"
    placementMobile: "bottom full-width inset"
---

# Product Design

## Project Scope

This document describes the current visible product experience for the Ledger
Simulator dashboard. The dashboard is an educational multi-currency ledger
console: users configure a sample transfer, execute it, inspect invariant
status, review journal rows, and observe reversal and concurrency-demo states.

This is not a public promotional site or high-concept product showcase. The
correct design genre is a compact learning tool with strong information
hierarchy and restrained visual polish.

## Experience Principles

- Lead with the working simulator. The first screen should expose the payment
  terminal, ledger status, and inspection surfaces rather than a promotional opener.
- Keep the interface dense but calm. The product is for repeated inspection of
  accounts, transactions, entries, and state changes.
- Use copy that reinforces educational scope: simulator, demo, learning
  console, backend, invariant, clearing accounts, race simulation.
- Make state visible. Balanced, failed, warning, reversed, and loading states
  should be readable from color, label, and placement.
- Preserve the current dashboard architecture: sidebar input controls on the
  left, ledger inspection surfaces on the right, then stacked layout on small
  screens.

## Information Architecture

### Desktop

The desktop shell is a two-column flex layout:

- Left: `Payment Terminal` sidebar, fixed at `320px`, sticky, full viewport
  height, scrollable if controls overflow.
- Right: main dashboard content, max width `1100px`, centered with `40px`
  padding.

The sidebar is the action surface. The main column is the explanation and audit
surface.

### Main Column Order

1. Settings gear in the top-right corner.
2. Page header: `Ledger Simulator` and educational subtitle.
3. Quick guide: Connect, Transfer, Verify, Stress.
4. Currency invariant card.
5. Metric strip: total debits, total credits, transactions, entries.
6. Payment flow card.
7. Accounts table.
8. Journal/ledger tabs.
9. Footer with sandbox/session status.

Do not move primary transfer controls into the main content unless the whole
dashboard layout is intentionally redesigned.

## Color System

The product uses semantic CSS variables prefixed with `--rev-*`. Keep the
palette short and functional.

### Base Surfaces

- `--rev-canvas`: page and sidebar background; `#ffffff` in light mode,
  `#000000` in dark mode.
- `--rev-surface`: panels, table containers, tab rails, invariant/flow cards;
  `#f4f4f4` in light mode, `#16181a` in dark mode.
- `--rev-input-bg`: form field background; `#ffffff` in light mode, `#0a0a0a`
  in dark mode.
- `--rev-border`: hairlines; `#e2e2e7` in light mode,
  `rgba(255,255,255,0.12)` in dark mode.

### Text

- `--rev-text`: primary text; `#191c1f` in light mode, `#ffffff` in dark mode.
- `--rev-text-mute`: helper text, labels, metadata; `#505a63` in light mode,
  `rgba(255,255,255,0.55)` in dark mode.

### Status And Accent

- Primary/cobalt: `#494fdf` light, `#4f55f1` dark. Use for guide accents,
  focus borders, active menu states, and count badges.
- Success/teal: `#00a87e`. Use for balanced states, debit direction, and
  successful feedback.
- Danger/red: `#e23b4a`. Use for credit direction, imbalance, errors, and
  reversal affordances.
- Warning/orange: `#ec7e00` and `#d97706`. Use for race simulation, backend
  wake/checking states, and caution feedback.

Do not introduce decorative gradients or extra accent families. Existing
gradients are state washes on guide cards and toasts, not page decoration.

## Typography

The implemented type stack is:

- `Inter Tight` for display, section, card, and metric headings.
- `Inter` for body, buttons, forms, labels, menus, and table content.
- `ui-monospace`, `SF Mono`, `Menlo`, `monospace` for flow diagrams, API URL
  input, idempotency key display, and code-like values.

### Type Scale

| Surface | Size | Weight | Notes |
|---|---:|---:|---|
| Page title | 42px desktop, 36px tablet, 32px mobile | 500 | `Inter Tight`, line-height 1.0 |
| Quick guide title | 24px desktop, 22px mobile | 600 | `Inter Tight` |
| Section title | 22px | 500 | Tables and flow headings |
| Sidebar title | 20px | 500 | Payment terminal |
| Guide card title | 17px | 600 | Compact card headings |
| Metric value | 32px desktop, 26px mobile | 600 | Large dashboard numerals |
| Body | 16px | 400 | Default readable copy |
| Table body | 14px | 400 | Data rows |
| Labels | 11px | 600 | Uppercase with 1.2px tracking |
| Helpers | 12px | 400 | Supporting hints and status text |

Avoid oversized promotional type. The dashboard title is intentionally compact so the
ledger state appears above the fold.

## Layout And Spacing

### Desktop

- `.app-container`: flex row, min-height `100vh`.
- `.sidebar`: `320px`, `32px 24px` padding, sticky top, full viewport height.
- `.main-content`: max width `1100px`, `40px` padding.
- `.quick-guide`: top and bottom hairlines, `22px 0 24px` padding.
- `.guide-grid`: four equal columns with `10px` gaps.
- `.metrics-grid`: four equal columns with `20px` gaps.
- Tables and major sections use `40px` bottom rhythm.

### Tablet And Narrow Desktop

At `max-width: 900px`:

- Shell stacks vertically.
- Sidebar becomes normal-flow, full-width, auto-height.
- Main content uses `32px 24px` padding.
- Settings gear becomes fixed at top-right.
- Quick guide becomes two columns.
- Metrics become two columns.
- Tables get horizontal scroll with a minimum table width.

### Mobile

At `max-width: 560px`:

- Sidebar padding becomes `22px 18px`.
- Main content padding becomes `28px 18px`.
- Page title becomes `32px`; lead text becomes `14px`.
- Quick guide becomes one column.
- Invariant card aligns content to the top and uses `18px` padding.
- Toasts move from top-right to bottom inset.
- Settings action buttons stack vertically.

## Component Guidance

### Payment Terminal Sidebar

The sidebar is the primary control panel. Preserve section order:

1. Sender and receiver.
2. Payment parameters.
3. Idempotency.
4. Concurrency strategy.
5. Execute, race simulation, and reset actions.

Use dividers between sections. Keep helper text close to the control it
explains. The idempotency key should look code-like and subdued.

### Buttons

- Primary action: full-width pill, `46px` tall, filled with current text color
  and inverted label. Used for `Execute Payment`.
- Secondary action: full-width pill, `42px` tall, transparent with border. Used
  for `Reset Database`.
- Warning action: full-width pill, `42px` tall, orange border/text. Used for
  `Simulate Concurrency Race`.
- Row-level reversal: compact bordered inline button with undo icon, danger
  hover state, and disabled state for already-reversed rows.

Do not use promotional CTAs or public-site button groups in this dashboard.

### Settings Popover

The settings gear is an icon-only control at the top-right of the main content.
The popover contains:

- Language menu.
- Appearance segmented control.
- Backend URL field, status, and Save/Default/Warm actions.

Keep the popover compact, bounded to the viewport, and close to the gear. On
mobile it becomes fixed and nearly full-width.

### Quick Guide

The quick guide is a compact onboarding aid, not a promotional opener. It explains four
actions:

- Connect.
- Transfer.
- Verify.
- Stress.

Guide cards use a 3px top accent bar and a soft vertical wash. The four accent
colors map to primary, success, danger, and warning. Cards use `8px` radius and
`16px` padding.

### Invariant Card

The invariant card is the main system-health signal. Use:

- Soft surface background.
- `20px` radius.
- Icon plus label/value stack.
- Teal for balanced state.
- Red for imbalance/error state.

The copy should be explicit about per-currency balancing.

### Metrics

Metric cards are intentionally unframed: label above value, with no card chrome.
This keeps the dashboard scan-friendly and avoids turning every number into a
competing tile.

### Flow Card

The flow card uses monospace text, horizontal overflow, and semantic coloring:

- Nodes and account names use primary text.
- Debit uses success/teal.
- Credit uses danger/red.
- FX clearing or highlight text may use cobalt.

The card should show the four-leg cross-currency path clearly without requiring
users to understand the underlying code.

### Tables

Tables are the audit surface. Use:

- Soft surface container.
- `12px` container radius.
- Uppercase table headers.
- `12px 16px` cell padding.
- Hairline row separators.
- Subtle cobalt wash for FX clearing rows.
- Horizontal scroll on narrow screens.

Never hide columns on mobile without an alternate way to inspect the same data.

### Tabs

The tab rail is a pill container with two choices:

- Journal Entries.
- Ledger Legs.

The selected tab uses the page canvas as the active fill and stronger text.
Inactive tabs remain muted.

### Toasts And Feedback

Toasts are fixed, stackable, and state-colored:

- Success: teal wash and border.
- Error: red wash and border.
- Warning: orange wash and border.

Use short titles and direct messages. Do not rely on color alone; text must
state what happened.

### Loading States

Skeleton states use muted opacity and border-colored placeholder blocks. Use
them while the backend state is loading, especially for invariant, metrics, and
flow surfaces.

## Interaction Rules

- The dashboard may start in a remote-backend wake state. Settings and status
  copy should make this recoverable without overwhelming the first screen.
- Every transfer or reset should produce visible feedback through a toast and
  refreshed ledger state.
- Race simulation feedback should use warning affordances before the run and
  success/error cards after the run.
- Reversal actions must read as append-only correction actions, not destructive
  edits.

## Responsive Rules

- Preserve all functionality across breakpoints.
- Stack the terminal before the dashboard on small screens so a user can
  configure a payment first.
- Keep tables horizontally scrollable rather than compressing data into
  unreadable cells.
- Keep the settings gear reachable even after the sidebar stacks above the main
  content.
- Avoid promo-only mobile layouts; mobile users still need access to controls,
  invariant status, and ledger tables.

## Accessibility Notes

- Controls have visible labels and associated inputs.
- The backend status region uses `aria-live`.
- Buttons should retain visible focus treatment through browser defaults or
  explicit border/background changes.
- Tables preserve headers and row structure.
- Status color must be paired with text labels such as `BALANCED BY CURRENCY`,
  `IMBALANCE DETECTED`, `REVERSED`, or `REVERSAL`.

## Do

- Keep the dashboard compact, inspectable, and working-first.
- Use the existing semantic colors consistently.
- Use `Inter Tight` sparingly for hierarchy and metrics.
- Keep labels uppercase and short.
- Let tables, flow text, and metrics carry the learning value.
- Document new UI states where they appear in `static/index.html` or
  `static/style.css`.

## Don't

- Do not add full-bleed promotional bands, device artwork, download-store tiles, or
  public-site navigation to this dashboard spec.
- Do not claim user scale, regulated status, or operational readiness in UI
  copy.
- Do not use decorative accent colors as primary buttons.
- Do not replace the sidebar terminal with a promotional composition unless the
  product goal changes.
- Do not hide ledger data for visual neatness.

## Known Gaps

- Focus states mostly rely on browser defaults plus a few component-specific
  hover/focus treatments.
- Tables are scrollable on mobile rather than redesigned into responsive row
  cards.
- The settings popover is lightweight and not a full modal dialog.
- The design doc describes the current dashboard; it does not cover a separate
  public promotional page or visual promotional system.
- Illustration, photography, and device artwork direction are intentionally
  out of scope for the current implementation.

## What To Update When The UI Changes

When changing visible UI, update this document if the change affects:

- Shell layout or breakpoints.
- Design tokens or CSS variables.
- Component sizing, radius, color, typography, or state behavior.
- User-facing dashboard copy.
- New simulator workflows, tables, tabs, toasts, or settings controls.
