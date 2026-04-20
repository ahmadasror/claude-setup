# FR — Orders Module

**Status**: Draft · **Generated**: 2026-04-20 by fr-writer · **Based on PRD**: v0.1, Architecture: v1.0

## Epic Breakdown

| Epic | Goal | Flows covered | Tickets |
|---|---|---|---|
| E-01 Submit & confirm | Customer berhasil place order end-to-end | F-01, F-02 | T-01..T-06 |
| E-02 Cancellation | Customer bisa cancel sebelum dispatch | F-03 | T-07..T-09 |
| E-03 Fulfillment handoff | Operator dispatch order | F-04 | T-10..T-12 |
| E-04 Returns | Customer initiate return & refund | F-05 | T-13..T-16 |
| E-05 Cross-cutting | Audit, idempotency, observability | all | T-17..T-20 |

## Flow Map (with FR refs)

| Flow | Tickets | Test scenarios |
|---|---|---|
| F-01 Submit happy path | T-01, T-02, T-03, T-04 | `docs/test-scenarios/orders/` |
| F-02 Payment declined | T-05, T-06 | idem |
| F-03 Customer cancel | T-07, T-08, T-09 | idem |
| F-04 Fulfillment dispatch | T-10, T-11, T-12 | idem |
| F-05 Return | T-13..T-16 | idem |

## Ticket Index

| ID | Title | Size | Epic | Workflow file |
|---|---|---|---|---|
| T-01 | Validate cart snapshot against catalog | M | E-01 | fr-order-submit.md |
| T-02 | Reserve inventory with TTL | M | E-01 | fr-order-submit.md |
| T-03 | Authorize payment | M | E-01 | fr-order-submit.md |
| T-04 | Persist order + emit CONFIRMED event | M | E-01 | fr-order-submit.md |
| T-05 | Handle payment decline — compensation | S | E-01 | fr-order-submit.md |
| T-06 | Confirmation UI (success + error states) | M | E-01 | fr-order-submit.md |
| T-07 | Cancel endpoint — state guard | S | E-02 | fr-order-cancel.md |
| T-08 | Release inventory on cancel | S | E-02 | fr-order-cancel.md |
| T-09 | Void/refund payment on cancel | M | E-02 | fr-order-cancel.md |
| T-10 | Dispatch transition + label generation | M | E-03 | fr-fulfillment-dispatch.md |
| T-17 | Idempotency-Key enforcement | M | E-05 | fr-order-submit.md |
| T-18 | State transition audit log | S | E-05 | *shared* |
| T-19 | X-Request-ID propagation | S | E-05 | *shared* |
| T-20 | Rate limit 5 PENDING per customer | S | E-05 | fr-order-submit.md |

## References

- PRD: `docs/prd/orders/`
- Architecture: `docs/architecture/orders/design.md`
- Completion status: `completion-status.md`
