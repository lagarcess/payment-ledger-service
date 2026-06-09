---
version: alpha
name: product-design
description: |
  The dashboard is a focused learning console for an educational multi-currency
  ledger simulator. It pairs a high-contrast black/white canvas with a restrained
  cobalt-violet accent (`#494fdf`) and semantic colors for ledger state: teal for
  debit/healthy signals, red for credit/error signals, and orange for pending or
  race-condition feedback. The design should feel precise, inspectable, and
  product-quality without implying regulated financial-service capability,
  compliance coverage, customer scale, or production payment readiness.

colors:
  primary: "#494fdf"
  primary-bright: "#4f55f1"
  primary-deep: "#3a40c4"
  on-primary: "#ffffff"
  ink: "#191c1f"
  body: "#1f2226"
  charcoal: "#3a3d40"
  mute: "#505a63"
  ash: "#5c5e60"
  stone: "#8d969e"
  faint: "#c9c9cd"
  on-dark: "#ffffff"
  on-dark-mute: "rgba(255,255,255,0.72)"
  canvas-light: "#ffffff"
  canvas-dark: "#000000"
  surface-soft: "#f4f4f4"
  surface-card: "#ffffff"
  surface-deep: "#0a0a0a"
  surface-elevated: "#16181a"
  hairline-light: "#e2e2e7"
  hairline-dark: "rgba(255,255,255,0.12)"
  hairline-strong: "#191c1f"
  divider-soft: "rgba(255,255,255,0.06)"
  accent-teal: "#00a87e"
  accent-blue-link: "#376cd5"
  accent-light-blue: "#007bc2"
  accent-light-green: "#428619"
  accent-green-text: "#006400"
  accent-yellow: "#b09000"
  accent-warning: "#ec7e00"
  accent-pink: "#e61e49"
  accent-danger: "#e23b4a"
  accent-deep-red: "#8b0000"
  accent-brown: "#936d62"
  link: "#376cd5"

typography:
  display-xxl:
    fontFamily: Inter Tight
    fontSize: 96px
    fontWeight: 600
    lineHeight: 1.0
    letterSpacing: -1.92px
  display-xl:
    fontFamily: Inter Tight
    fontSize: 64px
    fontWeight: 600
    lineHeight: 1.0
    letterSpacing: -0.64px
  display-lg:
    fontFamily: Inter Tight
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: -0.48px
  display-md:
    fontFamily: Inter Tight
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.4px
  heading-lg:
    fontFamily: Inter Tight
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.19
    letterSpacing: -0.32px
  heading-md:
    fontFamily: Inter Tight
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.33
    letterSpacing: 0
  heading-sm:
    fontFamily: Inter Tight
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.56
    letterSpacing: 0
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  body-md-bold:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: 0
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.43
  button-lg:
    fontFamily: Inter Tight
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.4
  button-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: 0
  button-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.43
  caption:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.4
  mono:
    fontFamily: ui-monospace
    fontSize: 13px
    fontWeight: 500
    lineHeight: 1.45

rounded:
  none: 0px
  sm: 8px
  md: 12px
  lg: 20px
  xl: 28px
  full: 9999px

spacing:
  xxs: 4px
  xs: 6px
  sm: 8px
  md: 14px
  lg: 16px
  xl: 24px
  xxl: 32px
  xxxl: 48px
  block: 80px
  section: 88px
  band: 120px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: 14px 20px
    height: 48px
  button-primary-pressed:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
  button-secondary:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: 14px 20px
    height: 48px
  button-danger:
    backgroundColor: "{colors.accent-danger}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: 14px 20px
    height: 48px
  button-warning:
    backgroundColor: "{colors.accent-warning}"
    textColor: "{colors.canvas-dark}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: 14px 20px
    height: 48px
  button-outline:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: 13px 19px
    height: 48px
  button-icon:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.button-sm}"
    rounded: "{rounded.full}"
    padding: 10px
    height: 40px
  text-input:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 14px 16px
    height: 56px
  range-input:
    trackColor: "{colors.hairline-light}"
    thumbColor: "{colors.primary}"
    height: 36px
  sidebar:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    width: 320px
  quick-guide-card:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 16px
  invariant-card:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 20px
  metric-card:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 18px
  data-table:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 0
  toast:
    backgroundColor: "{colors.canvas-light}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 16px 18px
---

# Product Design

## Purpose

This document describes the user-facing dashboard experience for the educational
multi-currency ledger simulator. It covers visual design, tokens, layout,
components, interaction behavior, responsive rules, and copy tone.

It does not define accounting behavior or backend safety rules. For those, see
[../engineering-design/DESIGN.md](../engineering-design/DESIGN.md).

## Scope

The interface is a learning console for exploring:

- double-entry ledger entries
- cross-currency FX clearing
- currency-aware invariant checks
- idempotency behavior
- reversals
- SQLite concurrency tradeoffs

The UI should feel precise and credible, but it must not imply that the project
is real payment infrastructure.

## Copy Safety

Use neutral, demonstrable language:

- "Educational ledger simulator"
- "Learning console"
- "Concept demo"
- "Currency-aware invariant"
- "FX clearing flow"
- "SQLite concurrency demo"

Avoid unsupported claims:

- unsupported scale or adoption claims
- regulated financial-service, compliance, or production-readiness claims
- copy that implies regulated payment processing
- marketing statements that describe scale the project does not have

Good heading examples:

- "Ledger Simulator"
- "Read the ledger in four moves"
- "Inspect the FX clearing legs"
- "Verify currency-aware balance"
- "Simulate a concurrency race"

Avoid headings that imply regulated payment capability, customer scale,
commercial plans, or production infrastructure.

## Overview

The dashboard operates in a high-contrast two-mode system: a light operational
canvas (`{colors.canvas-light}`) for tables, forms, and simulator state, paired
with a true-black dark mode (`{colors.canvas-dark}`) for users who prefer a
lower-glare inspection surface. The two modes should feel like the same product:
quiet, precise, and optimized for reading ledger state.

The visual rhythm is not a marketing page. It is an operational workspace with
enough polish to feel intentional: compact headings, restrained surfaces, crisp
tables, clear form controls, and visible state feedback.

The primary accent is `{colors.primary}` (`#494fdf`). Use it sparingly for
selected controls, focus, settings affordances, and important accent lines. The
semantic colors carry ledger meaning:

- `{colors.accent-teal}` for `DEBIT`, healthy invariant states, and success.
- `{colors.accent-danger}` for `CREDIT`, imbalance, destructive actions, and errors.
- `{colors.accent-warning}` for pending remote backend wake state and race demos.

**Key Characteristics:**

- Two-mode canvas system: white/light for default readability, true black for dark mode.
- Inter Tight headings plus Inter body/UI text.
- Dense but readable tables for accounts, transactions, and entry legs.
- A persistent payment terminal for simulator controls.
- Cobalt-violet accent used as a deliberate stamp, not a full-page theme.
- Color communicates ledger state; decoration stays secondary.

## Colors

### Brand & Accent

- **Cobalt Violet** (`{colors.primary}` — `#494fdf`): the main product accent. Use for primary actions, focus states, selected controls, and short accent bars.
- **Cobalt Bright** (`{colors.primary-bright}` — `#4f55f1`): dark-mode accent or hover variant.
- **Cobalt Deep** (`{colors.primary-deep}` — `#3a40c4`): active/pressed state for primary actions.
- **On-Primary** (`{colors.on-primary}` — `#ffffff`): text on primary surfaces.

### Surface

- **Canvas Light** (`{colors.canvas-light}` — `#ffffff`): default dashboard background and table surface.
- **Canvas Dark** (`{colors.canvas-dark}` — `#000000`): dark-mode page background.
- **Surface Soft** (`{colors.surface-soft}` — `#f4f4f4`): quiet panel and secondary button background.
- **Surface Card** (`{colors.surface-card}` — `#ffffff`): table and card surface in light mode.
- **Surface Deep** (`{colors.surface-deep}` — `#0a0a0a`): input and inset surface in dark mode.
- **Surface Elevated** (`{colors.surface-elevated}` — `#16181a`): dark-mode panel surface.
- **Hairline Light** (`{colors.hairline-light}` — `#e2e2e7`): 1px dividers in light mode.
- **Hairline Dark** (`{colors.hairline-dark}` — `rgba(255,255,255,0.12)`): 1px dividers in dark mode.
- **Hairline Strong** (`{colors.hairline-strong}` — `#191c1f`): high-contrast outlines where a control needs stronger definition.

### Text

- **Ink** (`{colors.ink}` — `#191c1f`): primary text in light mode.
- **Body** (`{colors.body}` — `#1f2226`): long-form text where ink feels too sharp.
- **Charcoal** (`{colors.charcoal}` — `#3a3d40`): secondary labels and captions.
- **Mute** (`{colors.mute}` — `#505a63`): helper text, metadata, table hints.
- **Ash** (`{colors.ash}` — `#5c5e60`): tertiary text.
- **Stone** (`{colors.stone}` — `#8d969e`): quiet metadata.
- **Faint** (`{colors.faint}` — `#c9c9cd`): disabled foreground.
- **On-Dark** (`{colors.on-dark}` — `#ffffff`): primary text in dark mode.
- **On-Dark Mute** (`{colors.on-dark-mute}` — `rgba(255,255,255,0.72)`): secondary text in dark mode.

### Semantic

- **Accent Teal** (`{colors.accent-teal}` — `#00a87e`): debit, success, healthy state.
- **Accent Light Blue** (`{colors.accent-light-blue}` — `#007bc2`): informational state, optional chart or link accent.
- **Accent Blue Link** (`{colors.accent-blue-link}` — `#376cd5`): default inline link on light surfaces.
- **Accent Light Green** (`{colors.accent-light-green}` — `#428619`): secondary success signal.
- **Accent Green Text** (`{colors.accent-green-text}` — `#006400`): compact positive inline text.
- **Accent Yellow** (`{colors.accent-yellow}` — `#b09000`): caution state.
- **Accent Warning** (`{colors.accent-warning}` — `#ec7e00`): backend wake, race demo, pending state.
- **Accent Pink** (`{colors.accent-pink}` — `#e61e49`): optional highlight; avoid using as a default action color.
- **Accent Danger** (`{colors.accent-danger}` — `#e23b4a`): credit, imbalance, destructive action, error state.
- **Accent Deep Red** (`{colors.accent-deep-red}` — `#8b0000`): compact error text when danger red needs more contrast.
- **Accent Brown** (`{colors.accent-brown}` — `#936d62`): rare neutral warmth; use sparingly.
- **Link** (`{colors.link}` — `#376cd5`): standard inline link.

## Typography

### Font Family

The system uses a two-family stack:

- **Inter Tight** — used for display headings and compact section titles.
- **Inter** — used for body text, controls, captions, tables, and metadata.

These are available through Google Fonts in the current static dashboard. If
fonts fail to load, fall back to `system-ui, sans-serif`.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---:|---:|---:|---:|---|
| `{typography.display-xxl}` | 96px | 600 | 1.0 | -1.92px | Rare full-viewport explanatory hero if one is ever added. |
| `{typography.display-xl}` | 64px | 600 | 1.0 | -0.64px | Major section opener outside the dense dashboard shell. |
| `{typography.display-lg}` | 48px | 600 | 1.12 | -0.48px | Large dashboard or report title. |
| `{typography.display-md}` | 40px | 600 | 1.15 | -0.4px | Main dashboard title when space allows. |
| `{typography.heading-lg}` | 32px | 600 | 1.19 | -0.32px | Major panel heading. |
| `{typography.heading-md}` | 24px | 600 | 1.33 | 0 | Quick guide and table section headings. |
| `{typography.heading-sm}` | 20px | 600 | 1.4 | 0 | Sidebar or component heading. |
| `{typography.body-lg}` | 18px | 400 | 1.56 | 0 | Introductory explanatory copy. |
| `{typography.body-md}` | 16px | 400 | 1.5 | 0 | Default body, form controls. |
| `{typography.body-md-bold}` | 16px | 600 | 1.5 | 0 | Emphasis and table values. |
| `{typography.body-sm}` | 14px | 400 | 1.43 | 0 | Helper text, table rows, metadata. |
| `{typography.button-lg}` | 18px | 600 | 1.4 | 0 | Primary large button label. |
| `{typography.button-md}` | 16px | 600 | 1.5 | 0 | Default button label. |
| `{typography.button-sm}` | 14px | 600 | 1.43 | 0 | Compact action or chip. |
| `{typography.caption}` | 13px | 400 | 1.4 | 0 | Footer, helper text, status captions. |
| `{typography.mono}` | 13px | 500 | 1.45 | 0 | Idempotency keys, transaction IDs, compact code-like values. |

### Principles

- Match type size to the work surface. Dashboards need compact hierarchy, not oversized marketing display type.
- Use Inter Tight for headings only. Use Inter for body, controls, captions, tables, and helper text.
- Keep letter spacing at `0` for most UI. Tight negative tracking belongs only on large display text.
- Use monospace styling only for values that benefit from fixed-width scanning: ids, keys, hashes, and amounts in tight columns.

### Note on Font Substitutes

If Inter Tight is unavailable, use Inter Display, General Sans, Söhne, or
system-ui. Keep dashboard headings modest and avoid aggressive negative tracking
inside panels.

## Layout

### Spacing System

- **Base unit**: 4px, with the working scale on multiples of 4 / 8 / 16.
- **Tokens**: `{spacing.xxs}` 4px, `{spacing.xs}` 6px, `{spacing.sm}` 8px, `{spacing.md}` 14px, `{spacing.lg}` 16px, `{spacing.xl}` 24px, `{spacing.xxl}` 32px, `{spacing.xxxl}` 48px, `{spacing.block}` 80px, `{spacing.section}` 88px, `{spacing.band}` 120px.
- Sidebar groups use 16-24px vertical spacing.
- Main sections use 24-40px spacing depending on density.
- Table cell padding should remain compact enough for repeated inspection.

### Grid & Container

- **Desktop shell**: fixed left terminal plus constrained main workspace.
- **Main content width**: approximately 1100-1200px for readable tables.
- **Quick guide grid**: 4-up at desktop, 2-up at tablet, 1-up at mobile.
- **Metric grid**: responsive columns that preserve label/value readability.
- **Tables**: allow horizontal scroll instead of dropping accounting columns.

### Whitespace Philosophy

- Use whitespace to separate reasoning steps: controls, invariant, metrics, tables.
- Do not pad table rows so much that ledger scanning becomes slow.
- Use hairline dividers for structure before adding shadows.
- Avoid nested cards. A panel can contain controls or a repeated item, but cards should not sit inside other cards unless the pattern has a clear functional purpose.

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| 0 - flat | No shadow, no border | Page canvas, table body rows. |
| 1 - panel | Hairline border on canvas/surface | Sidebar groups, quick guide cards, metric cards. |
| 2 - raised status | Subtle wash plus border | Invariant, toast, protected/offline state. |
| 3 - action emphasis | Primary/semantic color fill | Primary action, destructive reset, race warning. |
| 4 - modal/popover | Surface plus border and soft shadow | Settings popover, toast layer. |

The product should not depend on heavy drop shadows. Depth comes from surface
contrast, hairlines, position, and restrained shadows on overlays.

### Decorative Depth

- Quick guide cards may use a light wash and top accent bar to distinguish the four learning steps.
- Toasts may use a stronger shadow because they float above the app shell and must be noticed.
- Invariant and status cards should use semantic color washes tied to state.
- Avoid decorative orbs, atmospheric gradients, or stock-like imagery in the dashboard.

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---:|---|
| `{rounded.none}` | 0px | App shell, page bands, table dividers. |
| `{rounded.sm}` | 8px | Quick guide cards, badges, small chips. |
| `{rounded.md}` | 12px | Inputs, buttons, metric cards, invariant card. |
| `{rounded.lg}` | 20px | Larger overlays or empty-state panels. |
| `{rounded.xl}` | 28px | Rare large illustrative containers. |
| `{rounded.full}` | 9999px | Icon buttons, pills, toggles, status badges. |

### Geometry

- Tables should use stable columns and predictable row heights.
- Icon buttons should be square or circular with fixed dimensions.
- Range controls should reserve stable space for labels and current value.
- Toasts should have a bounded width and wrap long idempotency keys safely.
- Avoid layout shifts when status labels, translations, or dynamic amounts change.

## Components

### Buttons

**`button-primary`** - main simulator action

- Background `{colors.primary}`, label `{colors.on-primary}`, type `{typography.button-md}`, `rounded: {rounded.md}`, height 48px.
- Use for the main action that posts a simulator payment.
- Pressed/active state uses `{colors.primary-deep}`.

**`button-secondary`** - quiet secondary action

- Background `{colors.surface-soft}`, label `{colors.ink}`, type `{typography.button-md}`, `rounded: {rounded.md}`.
- Use for reset alternatives, save/settings controls, or low-risk secondary commands.

**`button-danger`** - destructive demo action

- Background `{colors.accent-danger}`, label `{colors.on-primary}`, type `{typography.button-md}`, `rounded: {rounded.md}`.
- Use when the action resets demo state or reverses a transaction.

**`button-warning`** - race/pending action

- Background `{colors.accent-warning}`, label `{colors.canvas-dark}`, type `{typography.button-md}`, `rounded: {rounded.md}`.
- Use for concurrency race simulation or pending/wake-related actions.

**`button-outline`** - secondary action on a plain surface

- Transparent or canvas background, label `{colors.ink}`, 1px solid `{colors.hairline-strong}`, type `{typography.button-md}`, `rounded: {rounded.md}`.
- Use when paired beside a filled button.

**`button-icon`** - icon-only utility action

- Square or circular, fixed 40px target minimum.
- Requires an accessible label or title.
- Use for settings, close, refresh, expand, and similar utilities.

### Cards & Containers

**`sidebar`** - payment terminal

- Persistent left-side control panel.
- Contains sender/receiver, amount, FX rate, idempotency, locking strategy, and primary actions.
- Keep it scannable; do not turn it into a marketing hero.

**`quick-guide-card`** - learning step card

- Background `{colors.canvas-light}`, text `{colors.ink}`, 1px solid `{colors.hairline-light}`, type `{typography.body-sm}`, `rounded: {rounded.sm}`, padding 16px.
- Uses a top accent bar to distinguish each step.
- Step labels should remain short: Connect, Transfer, Verify, Stress.

**`invariant-card`** - correctness signal

- Background should use a subtle state wash.
- Healthy state uses success/teal.
- Imbalance/error state uses danger/red.
- Pending/backend wake uses warning/orange.
- The text must say per-currency balancing when that is what is being checked.

**`metric-card`** - compact state summary

- Shows a label and a value.
- Use for total debits, total credits, transactions, entries, and accounts.
- Avoid business metrics that are not derived by the simulator.

**`data-table`** - ledger reading surface

- Rounded container with hairline dividers.
- Header labels use uppercase micro-label treatment.
- Rows should favor scanability and stable columns.
- Use color for direction and status, but include text labels.

**`settings-popover`** - backend and language controls

- Appears from the gear action.
- Should include language controls and backend origin controls.
- Keep copy concise; users should understand when the remote Render API may need warming.

**`toast`** - outcome notification

- Floats above the layout, not inside the sidebar stack.
- Uses `role="status"` for non-error messages and `role="alert"` for errors.
- Includes a close action.
- Wraps long text safely on mobile.

### Inputs & Forms

**`text-input`** - default input

- Background `{colors.canvas-light}`, text `{colors.ink}`, type `{typography.body-md}`, 1px solid `{colors.hairline-light}`, `rounded: {rounded.md}`, padding `14px 16px`, height 56px.
- Use for amount, API URL, custom idempotency key, and similar typed input.

**`select-input`** - account or mode selector

- Same sizing and border as `text-input`.
- Must show enough text to distinguish account name and currency.
- Avoid truncating the currency code.

**`range-input`** - FX rate control

- Track uses a quiet neutral; thumb uses `{colors.primary}`.
- Current value appears adjacent to the control.
- Derived destination amount should update immediately.

**`checkbox`** - binary setting

- Use for auto-generated idempotency key or similar binary settings.
- Label should describe the on-state.

### Navigation

**`app-shell`**

- The dashboard is the first screen.
- There is no marketing landing page before the simulator.
- Keep settings and language actions available without hiding the core workflow.

**`language-menu`**

- Should show explicit language names.
- Active language has a checkmark and clear selected state.

**`ledger-tabs`**

- Use tabs to switch between transaction journal and ledger legs.
- Active tab should have visible selection state.
- The tab label should describe the table content, not the implementation.

### Signature Components

**`currency-invariant-status`**

- Names the invariant and shows whether it is balanced.
- Should not claim global balancing is sufficient for multi-currency accounting.

**`entry-direction-badge`**

- `DEBIT` in success/teal.
- `CREDIT` in danger/red.
- Include the word and color; do not rely on color alone.

**`idempotency-key`**

- Use mono styling and safe wrapping.
- Preserve the full key somewhere visible or copyable.

**`backend-status`**

- Distinguish connected, offline, protected, and waking states.
- Protected should not look like generic offline failure.

## Do's and Don'ts

### Do

- Use the dashboard as the primary experience.
- Keep controls dense, legible, and predictable.
- Use `{colors.primary}` sparingly for focus and primary action.
- Use semantic colors for actual state: debit, credit, warning, error, success.
- Preserve the accounting labels in visible UI.
- Keep table columns stable and scannable.
- Make long keys and descriptions wrap without breaking layout.
- Keep copy educational and neutral.
- Point engineering behavior questions to the engineering design doc.

### Don't

- Don't reintroduce unsupported scale claims, regulated financial-service claims, compliance claims, or production-readiness claims.
- Don't build a marketing landing page in front of the dashboard.
- Don't use accent colors as arbitrary decorative surfaces.
- Don't hide ledger legs behind vague summary copy.
- Don't rely on color alone to distinguish debit/credit or success/error.
- Don't place cards inside cards unless the nested element is a modal, repeated item, or clearly framed tool.
- Don't loosen the UI into a one-note purple theme.
- Don't remove API/backend settings affordances from the dashboard.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---:|---|
| Desktop XL | >= 1440px | Sidebar plus wide table workspace; quick guide 4-up. |
| Desktop | 1280-1439px | Main container narrows; table columns remain visible. |
| Tablet Large | 1024-1279px | Sidebar can remain, but spacing tightens. |
| Tablet | 768-1023px | Guide cards 2-up; tables may scroll horizontally. |
| Mobile Large | 426-767px | Shell stacks; guide cards 1-up; buttons full width where useful. |
| Mobile | <= 425px | Single column; compact headings; preserve table data with horizontal scroll. |

### Touch Targets

- Primary buttons should be at least 48px tall.
- Icon buttons should be at least 40px, preferably 44px on mobile.
- Inputs should be at least 48px tall; amount and URL inputs can remain 56px.
- Toast close controls need reliable touch targets.

### Collapsing Strategy

- Sidebar and main workspace stack vertically below tablet width.
- Keep payment controls above tables on mobile so the sample flow remains usable.
- Quick guide cards collapse from 4-up to 2-up to 1-up.
- Ledger tables scroll horizontally rather than dropping currency, direction, or amount.
- Settings popover should stay within viewport bounds.

### Table Behavior

- Preserve account, currency, direction, and amount columns.
- Use horizontal overflow for narrow screens.
- Keep row labels readable and avoid clipping long transaction descriptions.
- Use dynamic wrapping for idempotency keys and descriptions.

### Toast Behavior

- Desktop: fixed top-right placement.
- Mobile: fixed with left/right bounds and auto width.
- Long error messages wrap with `overflow-wrap: anywhere`.

## Accessibility

- Maintain high contrast in light and dark themes.
- Provide focus states for controls.
- Give icon-only buttons labels or titles.
- Use `role="status"` and `role="alert"` appropriately for toasts.
- Avoid communicating ledger direction only by color.
- Keep keyboard navigation possible through sidebar controls, tabs, and settings.
- Avoid text overlap in translated strings.

## Interaction Guide

1. A user lands on the dashboard and sees a configured sample flow.
2. They can execute the payment without needing to read documentation first.
3. After execution, state refreshes and the new transaction is visible.
4. They can switch to ledger legs to inspect debit/credit postings.
5. They can retry an idempotency key and see duplicate behavior safely.
6. They can reverse a transaction using append-only correction.
7. They can switch locking mode and run the race simulation to learn concurrency tradeoffs.

Each interaction should make the concept more inspectable. Avoid hiding the
mechanics behind animations or vague success states.

## Iteration Guide

1. Focus on one component at a time.
2. Reference component names and tokens directly (`{colors.primary}`, `{component.invariant-card}`, `{rounded.md}`).
3. Keep UI copy in simulator scope.
4. Add variants as separate entries (`-pressed`, `-warning`, `-protected`, `-disabled`) rather than burying them in prose.
5. Default body type to `{typography.body-md}`.
6. Use `{typography.mono}` for ids, keys, and code-like values.
7. Keep `{colors.primary}` scarce; semantic colors should carry semantic state.
8. For any UI change, check desktop and mobile widths.
9. When adding a new educational concept, add both the control and the ledger/state view that makes it observable.

## Known Gaps

- Pressed/active visual states are documented most fully for primary actions; secondary controls could use a more complete state table.
- Transaction audit details could use a dedicated detail drawer or page.
- FX quote snapshots are auditable through the API but not fully surfaced in the dashboard.
- The reversal relationship is visible in transaction state but could be made clearer visually.
- Mobile table inspection works best with horizontal scrolling; a purpose-built mobile ledger row could be better.
- Visual regression checks are not yet automated.

## What I Would Refine With More Time

- Add a transaction detail drawer for entries, FX quote snapshot, fingerprint, and reversal relationship.
- Add a clearer visual pairing between original and reversal transactions.
- Add copy and UI states for idempotency retry versus idempotency conflict.
- Add a compact per-currency invariant breakdown.
- Add visual regression checks for desktop, tablet, and mobile.
- Add a richer empty/loading/waking/protected-backend state library.
