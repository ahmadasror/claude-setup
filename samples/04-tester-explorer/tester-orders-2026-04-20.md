# Test Scenarios — Orders

**Domain**: orders · **Generated**: 2026-04-20 by tester-explorer · **FR version**: Draft v0.1

> Progressive file — 3 phases. Phase 1 extracts workflow & state machine. Phase 2 maps seed data. Phase 3 generates scenarios + coverage matrix. User confirms between phases.

---

## Phase 1 — Workflow & State Machine

**Status**: ✅ Complete · Confirmed 2026-04-20

### Workflow (from PRD §order-submit)

1. Validate cart snapshot vs catalog
2. Reserve inventory (TTL 15m)
3. Authorize payment
4. Persist order (state=PENDING)
5. Transition PENDING → CONFIRMED
6. Async dispatch (fulfillment + notification)

### State Machine

```
            submit
           ───────►
                   ┌───────────┐
                   │  PENDING  │
                   └─────┬─────┘
          confirm ┌──────┴──────┐ timeout
                  ▼             ▼
          ┌─────────────┐  ┌───────────┐
          │  CONFIRMED  │  │ CANCELLED │
          └──┬──────────┘  └───────────┘
   ops.pack  │
             ▼
          ┌──────────┐
          │  PACKED  │──────► DISPATCHED ──► DELIVERED ──► RETURNED
          └──────────┘                                   (RMA flow)
```

Valid transitions:
- PENDING → CONFIRMED (on authorize success)
- PENDING → CANCELLED (timeout 15m or explicit)
- CONFIRMED → PACKED (ops action)
- CONFIRMED → CANCELLED (customer cancel, pre-dispatch)
- PACKED → DISPATCHED (ops dispatch)
- PACKED → CANCELLED (ops cancel)
- DISPATCHED → DELIVERED (carrier webhook)
- DELIVERED → RETURNED (RMA approved)

Invalid transitions (must reject):
- DELIVERED → CANCELLED
- DISPATCHED → CANCELLED (use return flow instead)
- Any → PENDING (terminal backward move)

### Business Rules Inventory

| BR | Source | Scope |
|---|---|---|
| BR-1 | PRD §BR-1 | Cart price drift ≤ 1% vs catalog |
| BR-2 | PRD §BR-2 | Inventory TTL 15 min |
| BR-3 | PRD §BR-3 | Idempotency 24h window |
| BR-4 | PRD §BR-4 | Order > USD 1,000 → flagged, async fraud |
| BR-5 | PRD §BR-5 | Max 5 PENDING per customer |

### AC Log (from FR)

AC-01..AC-11 tracked (see FR `fr-order-submit.md`). All 11 will map to ≥1 scenario in Phase 3 — any gap flagged.

---

## Phase 2 — Seed Data Map

**Status**: ✅ Complete · Confirmed 2026-04-20

### Seed catalog items

| SKU | Name | Price (USD) | State | Used by |
|---|---|---|---|---|
| SKU-ABC-001 | Alpha Widget | 25.00 | active | Happy path |
| SKU-ABC-002 | Beta Widget | 50.00 | active | Happy path multi-item |
| SKU-XYZ-777 | Deactivated Widget | 10.00 | deactivated | SKU_UNAVAILABLE |
| SKU-LOW-STK | Scarce Widget | 15.00 | active, stock=1 | Race condition CONC |
| SKU-HIGH-VAL | Premium Widget | 1250.00 | active | Flagged flow AC-08 |

### Seed customers

| Email (env var) | Role | Preconditions |
|---|---|---|
| `$TEST_CUSTOMER_NEW` | Customer | 0 existing orders |
| `$TEST_CUSTOMER_HEAVY` | Customer | 5 PENDING orders (for RATE_LIMITED) |
| `$TEST_CUSTOMER_DECLINE` | Customer | payment method configured to always decline |
| `$TEST_OPS_OPERATOR` | Fulfillment | access to WMS console |

Credentials via env vars (see `CLAUDE.md` — never hardcoded in test files).

### Seed payment methods (test gateway tokens)

| Token | Behavior |
|---|---|
| `$PM_SUCCESS` | authorize success |
| `$PM_DECLINE` | authorize decline |
| `$PM_TIMEOUT` | authorize hang 11s (beyond 10s timeout) |

### Precondition templates

**PRE-FRESH-CUSTOMER**: new customer, empty order history, valid address + payment method.
**PRE-AT-LIMIT**: customer with exactly 5 PENDING orders, next submit should RATE_LIMITED.
**PRE-CART-DRIFT**: submit while background process flips catalog price > 1%.
**PRE-RESERVATION-EXPIRED**: reserve inventory, wait 16 min, then authorize.

### Gaps flagged

- **MISSING — seed for return flow** — PRD §order-return belum punya FR; tunda sampai FR tersedia.

---

## Phase 3 — Test Scenarios

**Status**: ✅ Complete

### Scenarios

#### HP — Happy Path

| ID | Title | Preconditions | Steps | Expected | AC |
|---|---|---|---|---|---|
| ORDERS-HP-001 | Submit single-item order | PRE-FRESH-CUSTOMER | Submit cart with SKU-ABC-001 × 1 | 201, state=CONFIRMED, order_number format ORD-2026-NNNNN | AC-01, AC-11 |
| ORDERS-HP-002 | Submit multi-item order | PRE-FRESH-CUSTOMER | Cart with SKU-ABC-001 × 2 + SKU-ABC-002 × 1 | 201, total_amount = 100.00 | AC-01 |
| ORDERS-HP-003 | Order > USD 1,000 flagged | PRE-FRESH-CUSTOMER | Cart with SKU-HIGH-VAL × 1 | 201, state=CONFIRMED, flagged=true | AC-08 |

#### SP — Sad Path

| ID | Title | Preconditions | Steps | Expected | AC |
|---|---|---|---|---|---|
| ORDERS-SP-001 | Missing Idempotency-Key | PRE-FRESH-CUSTOMER | Submit without header | 400, code=VALIDATION_ERROR | AC-05 |
| ORDERS-SP-002 | Unauthenticated | no session | Submit with invalid token | 401, code=UNAUTHENTICATED | — |
| ORDERS-SP-003 | Deactivated SKU | PRE-FRESH-CUSTOMER | Submit cart with SKU-XYZ-777 | 410, code=SKU_UNAVAILABLE | AC-02 |

#### BR — Business Rules

| ID | Title | Preconditions | Steps | Expected | AC |
|---|---|---|---|---|---|
| ORDERS-BR-001 | Price drift > 1% | PRE-CART-DRIFT | Submit with stale cart price | 409, code=PRICE_DRIFT, no reservation | AC-02 |
| ORDERS-BR-002 | Insufficient stock | SKU-LOW-STK stock=0 | Submit 1 unit | 409, code=INSUFFICIENT_STOCK | AC-03 |
| ORDERS-BR-003 | Payment declined | payment=$PM_DECLINE | Submit valid cart | 402, code=PAYMENT_DECLINED, inventory released | AC-04 |
| ORDERS-BR-004 | Reservation expired | PRE-RESERVATION-EXPIRED | Retry submit | 409, code=RESERVATION_EXPIRED | AC-09 |
| ORDERS-BR-005 | Rate limited at 6th PENDING | PRE-AT-LIMIT | Submit 6th order | 429, code=RATE_LIMITED | AC-07 |

#### IDEM — Idempotency

| ID | Title | Preconditions | Steps | Expected | AC |
|---|---|---|---|---|---|
| ORDERS-IDEM-001 | Replay same key < 24h | PRE-FRESH-CUSTOMER | Submit with key X, repeat same payload | Both 201, same order_id returned | AC-05 |
| ORDERS-IDEM-002 | Same key, different payload | — | Submit with key X payload A, then payload B | 2nd = 409 DUPLICATE_ORDER | AC-05 |
| ORDERS-IDEM-003 | Same key after 24h | — | Submit at T, again at T+24h01m | Both 201, 2 distinct orders | AC-06 |

#### ST — State Transition (valid)

| ID | Title | From | Action | Expected |
|---|---|---|---|---|
| ORDERS-ST-001 | PENDING → CONFIRMED | PENDING | Payment authorize success | state=CONFIRMED, audit row appended |
| ORDERS-ST-002 | CONFIRMED → PACKED | CONFIRMED | Ops pack action | state=PACKED |
| ORDERS-ST-003 | PACKED → DISPATCHED | PACKED | Ops dispatch | state=DISPATCHED, shipping label issued |
| ORDERS-ST-004 | CONFIRMED → CANCELLED | CONFIRMED | Customer cancel | state=CANCELLED, inventory released, payment voided |

#### STX — State Transition (invalid)

| ID | Title | From | Action | Expected |
|---|---|---|---|---|
| ORDERS-STX-001 | Cancel DISPATCHED | DISPATCHED | Customer cancel | 409, code=INVALID_TRANSITION |
| ORDERS-STX-002 | Cancel DELIVERED | DELIVERED | Customer cancel | 409, code=INVALID_TRANSITION (use return instead) |
| ORDERS-STX-003 | Backward to PENDING | CONFIRMED | Any action targeting PENDING | rejected |

#### AUTH — Authorization

| ID | Title | Actor | Target | Expected |
|---|---|---|---|---|
| ORDERS-AUTH-001 | Customer cancels other customer's order | Customer A | Customer B's order | 403, code=FORBIDDEN |
| ORDERS-AUTH-002 | Customer dispatches own order | Customer | own PACKED order | 403 — only ops can dispatch |

#### CONC — Concurrency

| ID | Title | Setup | Action | Expected |
|---|---|---|---|---|
| ORDERS-CONC-001 | Two customers race last stock | SKU-LOW-STK stock=1 | Both submit concurrently | 1 success, 1 INSUFFICIENT_STOCK |
| ORDERS-CONC-002 | Same customer double-click submit | PRE-FRESH-CUSTOMER | Two submits same idempotency key simultaneous | 1 order created, 2nd replays |

#### AUDIT — Audit Trail

| ID | Title | Verify |
|---|---|---|
| ORDERS-AUDIT-001 | State transition append | Each transition = exactly 1 row in order_state_history with actor, timestamp, X-Request-ID |
| ORDERS-AUDIT-002 | Audit immutable | UPDATE attempt on audit table rejected at DB level |

#### EDGE — Boundary

| ID | Title | Input | Expected |
|---|---|---|---|
| ORDERS-EDGE-001 | Cart price exactly 1% drift | Price at 1.00% of catalog | 201 accepted (AC-02 says ">1%") |
| ORDERS-EDGE-002 | Cart price 1.01% drift | Just above threshold | 409 PRICE_DRIFT |
| ORDERS-EDGE-003 | Order total USD 1,000.00 exact | | 201, flagged=false (>, not ≥) |
| ORDERS-EDGE-004 | Order total USD 1,000.01 | | 201, flagged=true |

### Coverage Matrix

| AC | Covered by |
|---|---|
| AC-01 | ORDERS-HP-001, HP-002, ST-001 |
| AC-02 | ORDERS-BR-001, SP-003, EDGE-001, EDGE-002 |
| AC-03 | ORDERS-BR-002, CONC-001 |
| AC-04 | ORDERS-BR-003 |
| AC-05 | ORDERS-IDEM-001, IDEM-002, SP-001 |
| AC-06 | ORDERS-IDEM-003 |
| AC-07 | ORDERS-BR-005 |
| AC-08 | ORDERS-HP-003, EDGE-003, EDGE-004 |
| AC-09 | ORDERS-BR-004 |
| AC-10 | *Load test — separate from functional scenarios* |
| AC-11 | ORDERS-AUDIT-001, ST-001 |

**Gaps**:
- AC-10 (latency NFR) — not a functional scenario; tracked in load-test plan separately. Flagged as gap for this suite.

### References

- PRD: `docs/prd/orders/order-submit.md`
- FR: `docs/fr/orders/fr-order-submit.md`
- Next: `test-builder` reads this file + seed data map to generate Playwright specs
