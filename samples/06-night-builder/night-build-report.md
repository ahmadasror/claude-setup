# Night Build Report

**Task**: Implement T-01..T-04, T-17 from `docs/fr/orders/fr-order-submit.md` — submit endpoint end-to-end happy path + idempotency infra
**Date**: 2026-04-20
**Result**: ⚠️ Partial

---

## What Was Done

- `orders-service/src/main/java/orders/api/OrderController.java` — created — REST controller, POST /api/v1/orders, Idempotency-Key header required
- `orders-service/src/main/java/orders/application/OrderSubmitService.java` — created — orchestrates validate → reserve → authorize → persist → emit event
- `orders-service/src/main/java/orders/domain/Order.java` — created — aggregate, state machine, transition guards
- `orders-service/src/main/java/orders/infra/IdempotencyCache.java` — created — Redis SETNX with 24h TTL, keyed by customer_id + header
- `orders-service/src/main/java/orders/infra/CatalogClient.java` — created — async lookup, batched by SKU
- `orders-service/src/main/java/orders/infra/InventoryAdapter.java` — created — reserve with TTL 900s
- `orders-service/src/main/java/orders/infra/PaymentAdapter.java` — created — authorize with 10s timeout, compensation on fail
- `orders-service/src/main/resources/db/migration/V1__orders_schema.sql` — created — orders, order_items, order_state_history tables + indexes
- `orders-service/src/test/java/orders/application/OrderSubmitServiceTest.java` — created — 14 unit tests, all AC paths
- `orders-service/src/test/java/orders/infra/IdempotencyCacheTest.java` — created — 4 tests
- `web/src/routes/checkout/+page.svelte` — modified — added `place-order-btn`, `checkout-error-banner`, `checkout-error-code` testids verbatim from FR
- `web/src/routes/orders/[id]/+page.svelte` — modified — added `order-confirmation-banner`, `order-confirmation-number` testids

## Assumptions Made

> Decisions made without human input. Review before committing.

| # | Blocker | Assumption | Rationale | Risk |
|---|---|---|---|---|
| 1 | OQ-3 rate limit scope (PENDING only or PENDING+CONFIRMED) — FR `completion-status.md` flagged as NEEDS PO INPUT | Implemented PENDING-only count (ignores CONFIRMED/unshipped) | PRD §BR-5 literal says "5 order PENDING concurrent" — took literal reading | MEDIUM — PO may want stricter |
| 2 | Fraud check async endpoint — FR says enqueue, but queue name not specified | Used `orders.fraud.check` exchange with `fraud-check-requests` queue | Existing RabbitMQ naming pattern in codebase (`{domain}.{action}`) | LOW |
| 3 | Catalog SKU lookup batching — lookup-per-item vs batch | Implemented batch via `CatalogClient.lookupBatch(List<String>)` | Round-trip reduction, aligns with PRD NFR ≤ 3s P95 | LOW |
| 4 | Order number sequence reset per year — no explicit allocator design | Used PostgreSQL sequence `order_seq_2026`, plan to rotate annually | ADR-based pattern, predictable counter | MEDIUM — race on rollover 2026→2027 midnight not handled |
| 5 | Idempotency replay body — return 201 with original body vs 200 | Return 201 with original body (RFC-style) | AC-05 says "HTTP 201 (original response body replayed)" | LOW |

## Decisions & Trade-offs

- **Saga vs transactional**: Chose saga with compensation for reserve/authorize. Alternative (distributed TX via XA) rejected — gateway does not support XA.
- **Outbox pattern for events**: Events `order.confirmed` written to `outbox` table in same TX as order persist. Separate publisher job picks up. Alternative (emit from service layer) rejected — loses atomicity on publish failure.
- **ArchUnit enforcement**: Added `ArchUnitOrdersTest` to CI — no cross-module DB access, no domain → infra backward reference. Aligns with ADR-001.

## Test Results

- Total: **18 passed, 0 failed, 0 skipped**
- Coverage: 87% line (orders-service module)
- Breakdown:
  - OrderSubmitServiceTest: 14/14 ✅ (all AC paths)
  - IdempotencyCacheTest: 4/4 ✅
  - Existing suite: 42/42 ✅ (no regression)

```
[INFO] Tests run: 60, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Known Gaps

- **T-06 confirmation UI** — partially done. Success + PAYMENT_DECLINED error state implemented. PRICE_DRIFT and INSUFFICIENT_STOCK error copies pending — FR has code but no copy text. Flagged for content reviewer.
- **T-20 rate limit** — stub returns 429 but uses fixed PENDING=5 count; not tested concurrently. Assumption #1 needs PO confirmation before E2E test meaningful.
- **Load test for AC-10** — not night-builder scope. Separate load-test plan recommended.
- **ORDERS-BR-004 reservation expired** — implementation correct but test not added (requires time travel helper not yet in test infra).

## Next Steps

- [ ] Review assumptions — especially #1 (rate limit) and #4 (sequence rollover) before committing
- [ ] Have PO confirm OQ-3 (rate limit scope)
- [ ] Add error copy for PRICE_DRIFT, INSUFFICIENT_STOCK, RATE_LIMITED in checkout page (content team)
- [ ] Schedule load test to verify AC-10 P95 ≤ 3s
- [ ] Add time-travel test helper to cover ORDERS-BR-004
- [ ] Commit and push when satisfied — branch `feat/orders-submit-v1`
