# FR Completion Status — Orders

**Generated**: 2026-04-20 by fr-writer

## Build Order (recommended)

1. T-17 Idempotency-Key infra (blocks everything — must be first)
2. T-01, T-02, T-03 in parallel (validate, reserve, authorize)
3. T-04 persist + emit
4. T-05 compensation (needs T-02, T-03)
5. T-06 confirmation UI (needs T-04 response shape)
6. T-18, T-19 cross-cutting audit + X-Request-ID (parallel with above, infra-level)
7. T-07..T-09 cancel flow
8. T-10..T-12 dispatch flow
9. T-13..T-16 return flow

## Open Questions

| # | Question | Blocks | Status |
|---|---|---|---|
| OQ-1 | Fraud check SLA — sync atau async? PRD §BR-4 ambiguous | T-04, T-08 | Assumed async, flagged=true (see AD-1) |
| OQ-2 | Reservation TTL 15 menit — dari PRD §BR-2, tapi payment timeout 10s di design. Worst case terbuka 25s window. OK? | T-02 | Assumed OK per design.md §Concurrency |
| OQ-3 | Rate limit 5 PENDING — apakah PENDING + CONFIRMED (unshipped) atau PENDING only? | T-20 | **NEEDS PO INPUT** |
| OQ-4 | Partial cancel (1 item dari multi-item order)? | T-07 | Out of scope v1 — v2 backlog |

## Assumed Decisions

| # | Decision | Rationale | Risk | Override path |
|---|---|---|---|---|
| AD-1 | Fraud check async; order state=CONFIRMED, flagged=true | PRD §BR-4 menyebut "additional fraud check (async)" | LOW | Bila PO prefer sync block, update T-04 + AC-08 |
| AD-2 | `order_number` format `ORD-YYYY-NNNNN` dengan NNNNN reset per year | PRD §Data Model contoh format | LOW | Non-breaking rename |
| AD-3 | Currency fixed USD v1 | PRD Out of Scope §Multi-currency v2 | LOW | v2 scope |
| AD-4 | Response envelope `{code, message, trace_id, details}` | Arsitektur design.md | LOW | Breaking change — koordinasi dengan API consumers |

## Gaps (FR belum cover)

- **Return flow ACs** (E-04, T-13..T-16) — placeholder, belum detail AC per step. Butuh PRD workflow `order-return.md` selesai dulu.
- **Operator console UX** untuk F-04 dispatch — PRD wireframe masih TBD.

## DoR / DoD signals

- ✅ PRD available dan stabil
- ✅ Architecture design.md + ADR-001 available
- ⚠ PO review OQ-3 before T-20 commit
- ✅ UI Selectors section complete untuk F-01/F-02 pages

## References

- FR index: `index.md`
- PRD: `docs/prd/orders/`
