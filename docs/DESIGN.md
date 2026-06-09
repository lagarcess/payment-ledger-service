# Design Documents

This repository has two separate design concerns. They are intentionally kept in
different folders so product/UI decisions do not overwrite ledger/accounting
design notes.

## Product Design

See [product-design/DESIGN.md](product-design/DESIGN.md).

This document covers the user-facing dashboard experience: visual language,
copy tone, layout, components, responsive behavior, and interaction principles.
Use it when changing `static/index.html`, `static/style.css`, or
`static/script.js` in ways that affect what users see.

## Engineering Design

See [engineering-design/DESIGN.md](engineering-design/DESIGN.md).

This document covers ledger behavior and implementation design: accounting
convention, data model, balance derivation, currency-aware invariants, FX
clearing, idempotency, reversals, concurrency, known limitations, and the
technical roadmap.

## Copy Safety

This project is an educational simulator. Product-facing copy should describe
what the demo actually does and avoid unsupported claims about customers, scale,
regulated financial-service readiness, compliance coverage, or production
payment infrastructure.
