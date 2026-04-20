# FR — order-submit

**Workflow**: order-submit · **Flows**: F-01, F-02 · **Epic**: E-01, E-05

## Scope

Customer submit order → validate → reserve inventory → authorize payment → persist → confirm. Termasuk error path untuk decline, price drift, out-of-stock, duplicate idempotency key.

## Acceptance Criteria

| AC ID | Condition | Expected |
|---|---|---|
| AC-01 | Customer submit dengan cart valid + payment method valid | HTTP 201, state=CONFIRMED, confirmation email dispatched, response ≤ 3s P95 |
| AC-02 | Cart price > 1% drift dari katalog saat submit | HTTP 409, code=PRICE_DRIFT, inventory tidak di-reserve, payment tidak di-authorize |
| AC-03 | SKU out of stock saat reserve | HTTP 409, code=INSUFFICIENT_STOCK, payment tidak di-authorize |
| AC-04 | Payment gateway return decline | HTTP 402, code=PAYMENT_DECLINED, inventory reservation released, order tidak tercipta |
| AC-05 | Same Idempotency-Key re-submit dalam 24h | HTTP 201 (original response body replayed), order tidak duplicate |
| AC-06 | Same Idempotency-Key re-submit setelah 24h | HTTP 201, order baru tercipta |
| AC-07 | Customer dengan 5 PENDING concurrent submit order ke-6 | HTTP 429, code=RATE_LIMITED |
| AC-08 | Order total > USD 1,000 | HTTP 201, state=CONFIRMED, flagged=true, async fraud check enqueued |
| AC-09 | Reservation TTL (15 menit) expired sebelum payment authorize | HTTP 409, code=RESERVATION_EXPIRED, retry required |
| AC-10 | Latency NFR | P95 ≤ 3s, P99 ≤ 8s diukur di kritikal path (reserve + authorize + persist) |
| AC-11 | Audit trail | Setiap state transition (PENDING → CONFIRMED) append 1 row ke order_state_history dengan actor, timestamp, request_id |

## API Response Codes

| Code | HTTP | Trigger | Endpoint |
|---|---|---|---|
| - | 201 | Success | POST /api/v1/orders |
| PRICE_DRIFT | 409 | Cart price drift > 1% | POST /api/v1/orders |
| SKU_UNAVAILABLE | 410 | SKU deactivated | POST /api/v1/orders |
| INSUFFICIENT_STOCK | 409 | Inventory reserve fail | POST /api/v1/orders |
| PAYMENT_DECLINED | 402 | Gateway decline | POST /api/v1/orders |
| RESERVATION_EXPIRED | 409 | TTL expired before authorize | POST /api/v1/orders |
| DUPLICATE_ORDER | 409 | Idempotency-Key conflict (different payload) | POST /api/v1/orders |
| RATE_LIMITED | 429 | 5 PENDING per customer exceeded | POST /api/v1/orders |
| VALIDATION_ERROR | 400 | Schema invalid | POST /api/v1/orders |
| UNAUTHENTICATED | 401 | Missing/invalid auth | POST /api/v1/orders |

## UI Selectors

> `data-testid` contract — published API. Night-builder implement verbatim, test-builder consume verbatim. Lihat `docs/architecture/testing/ui-selector-contract.md`.

| testid | Page | Component | Role | AC |
|---|---|---|---|---|
| `place-order-btn` | /checkout | Button | Primary submit action | AC-01 |
| `checkout-total` | /checkout | StatCard | Display computed total | AC-01, AC-02 |
| `order-confirmation-banner` | /orders/{id} | Alert | Success banner post-submit | AC-01 |
| `order-confirmation-number` | /orders/{id} | Text | Show order number | AC-01 |
| `checkout-error-banner` | /checkout | Alert | Error message container | AC-02, AC-03, AC-04, AC-07 |
| `checkout-error-code` | /checkout | Text | Error code chip (PRICE_DRIFT etc) | AC-02..AC-07 |
| `retry-payment-btn` | /checkout | Button | Retry action on decline | AC-04 |

## Tickets

### T-01 — Validate cart snapshot against catalog

**Epic**: E-01 · **Domain**: Orders · **Type**: Story · **Size**: M

**AC**:
- AC-02 (PRICE_DRIFT path) implemented
- Catalog lookup parallelized per SKU (async)
- SKU_UNAVAILABLE returned untuk SKU deactivated

**Notes**: Gunakan existing `CatalogClient` di `shared/clients/`. Jangan call per-item sync — loop async.

---

### T-02 — Reserve inventory with TTL

**Epic**: E-01 · **Domain**: Inventory (adapter) · **Type**: Story · **Size**: M

**AC**:
- AC-03 (INSUFFICIENT_STOCK path)
- Reservation TTL 15 menit — encode via Inventory service API `ttl_seconds=900`
- Compensation: release pada payment fail (T-05)

---

### T-03 — Authorize payment

**Epic**: E-01 · **Domain**: Payment (adapter) · **Type**: Story · **Size**: M

**AC**:
- AC-04 (PAYMENT_DECLINED path)
- Timeout 10s — treat as decline + compensate
- `Idempotency-Key` forwarded ke gateway

---

### T-04 — Persist order + emit CONFIRMED event

**Epic**: E-01 · **Domain**: Orders · **Type**: Story · **Size**: M

**AC**:
- AC-01, AC-08 (flagged > USD 1,000), AC-11 (audit)
- State transition PENDING → CONFIRMED append row di order_state_history
- Outbox event `order.confirmed` untuk fulfillment + notification dispatch

---

### T-17 — Idempotency-Key enforcement

**Epic**: E-05 · **Domain**: Orders · **Type**: Story · **Size**: M

**AC**:
- AC-05 (replay), AC-06 (fresh after 24h)
- Header `Idempotency-Key` mandatory — VALIDATION_ERROR bila absent
- Redis SETNX keyed `idem:{customer_id}:{key}`, TTL 86400

---

### T-06 — Confirmation UI (success + error states)

**Epic**: E-01 · **Domain**: Frontend · **Type**: Story · **Size**: M

**AC**:
- AC-01 success banner render
- AC-02..AC-04 error banner dengan code mapping ke copy human-readable
- UI Selectors section di atas di-implement verbatim

**Notes**: Gunakan komponen `Alert` + `StatCard` existing di DS. Jangan invent testid baru.

## Open Questions

Lihat `completion-status.md` untuk open questions & assumed decisions.

## References

- PRD: `docs/prd/orders/order-submit.md`
- Architecture: `docs/architecture/orders/design.md`
- Test scenarios: `docs/test-scenarios/orders/` *(to be generated by tester-explorer)*
