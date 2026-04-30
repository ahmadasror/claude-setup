# Drift Triage Report — 2026-04-30

**Source**: `docs/drift-reports/2026-04-30/report-drift.json` (generated 2026-04-30T03:14:22Z)
**Total entries**: 14
**Triage date**: 2026-04-30
**Module scope**: `orders`

---

## Classification Summary

| Class | Count | Recommended path |
|---|---|---|
| FR-ahead | 3 | night-builder |
| Code-ahead | 2 | fr-writer |
| Real-mismatch | 5 | manual_review |
| Waiver-eligible | 1 | accept (expires 2026-05-15) |
| Stale (file removed) | 0 | — |
| Schema-invalid | 0 | — |
| Other (per-link sub-class) | 3 | (see Detail) |

## By Severity

| Severity | Count | Notable |
|---|---|---|
| P0 | 2 | `orders-service`/order_authorize_handler.go: `audit:skip` missing on a CUD path |
| P1 | 7 | error code mismatch on POST /api/v1/orders, 5 ACs uncovered |
| P2 | 4 | field naming, marker_tbd ledger entry approaching 60d |
| P3 | 1 | informational — orders PRD missing block (gradient adoption) |

## Drift kind distribution

| Kind | Reason | Count |
|---|---|---|
| `endpoint` | response code mismatch | 2 |
| `permission` | role/permission mismatch | 1 |
| `db_*` | column type drift | 1 |
| `code_comment` | `marker_missing` | 2 |
| `code_comment` | `marker_orphan_fr` | 1 |
| `code_comment` | `marker_tbd` | 1 |
| `test_coverage` | `ac_uncovered` | 3 |
| `tc_orphan` | `traces_to_unknown_fr` | 1 |
| `test_ratchet` | `regression` | 1 |
| `prd_link` | `prd_no_block` | 1 |

---

## Hotspots (FR files with ≥3 drift entries)

| FR file | Drift count | Dominant class |
|---|---|---|
| docs/fr/orders/fr-order-submit.md | 6 | Real-mismatch |
| docs/fr/orders/fr-order-fulfill.md | 4 | FR-ahead |

---

## Recommendations (queue order)

### To night-builder (FR-ahead — 3 entries)

| # | Target file | Drift entries | FR | Notes |
|---|---|---|---|---|
| 1 | `orders-service/.../order_fulfill_handler.go` | drift-005, drift-006 | docs/fr/orders/fr-order-fulfill.md | Endpoint POST `/api/v1/orders/{id}/fulfill` declared in FR but no route handler exists |
| 2 | `orders-service/.../inventory_repository.go` | drift-008 | docs/fr/orders/fr-order-submit.md | Column `inventory.reserved_until` declared in FR but missing in migrations |

### To fr-writer (Code-ahead — 2 entries)

| # | Target FR | Drift entries | Code source | Notes |
|---|---|---|---|---|
| 1 | docs/fr/orders/fr-order-submit.md | drift-002 | `orders-service/.../order_recover_handler.go` | Endpoint `POST /api/v1/orders/{id}/recover` exists but no FR claim. Either extend FR or remove dead code |
| 2 | docs/fr/orders/fr-order-cancel.md | drift-009 | new column `orders.cancellation_reason_code` | Column exists in migrations V42 but no FR mentions it |

### To tester-explorer (L4 — 4 entries)

| # | Target | Drift entries | Reason | Notes |
|---|---|---|---|---|
| 1 | docs/test-scenarios/orders/api/flow-01-submit.md | drift-011, drift-012, drift-013 | `ac_uncovered` × 3 | FR-ORD-001 AC-7 (idempotency replay), AC-9 (reservation TTL), AC-10 (latency NFR) have no TC. Author or set FR `test_coverage.required: false` for AC-10 |
| 2 | docs/test-scenarios/orders/api/flow-02-fulfill.md | drift-014 | `traces_to_unknown_fr` | TC-ORD-002-HP-001 cites `FR-ORD-NEW-001` — no such FR exists. Likely typo for `FR-ORD-002` |

### Manual review needed (Real-mismatch + low-confidence — 5 entries)

| # | FR | Code | Drift entries | Why manual |
|---|---|---|---|---|
| 1 | docs/fr/orders/fr-order-submit.md | `OrderSubmitController.java` | drift-001 | **P0** — Permission claim `orders.submit` vs code `orders.create`. Decide: rename FR claim or add new permission constant. Both touch downstream RBAC table |
| 2 | docs/fr/orders/fr-order-submit.md | `OrderSubmitController.java` | drift-003 | **P1** — Error code claim `PRICE_DRIFT` vs code `PRICE_CHANGED`. FR last edited 3 days ago, code 8 weeks ago — likely FR ahead |
| 3 | docs/fr/orders/fr-order-submit.md | `OrderSubmitService.java` | drift-007 | **P0** — `audit:skip` marker missing on `cancelByCustomer()` (CUD path). Either add `audit.Log()` and remove sentinel, or add explicit `// audit:skip — cascade emit covers this` |
| 4 | docs/fr/orders/fr-order-submit.md | `Order.java` | drift-004 | **P1** — Status enum claim `[PENDING, CONFIRMED, FULFILLED, CANCELLED]` vs code `[NEW, CONFIRMED, FULFILLED, CANCELLED]`. Migration would rename DB enum — needs ADR |
| 5 | (orphan) | `audit_writer.go` | drift-010 | **P0** — `marker_orphan_fr` — leading comment cites `FR-ORD-099 AC-1` but no FR-ORD-099 exists. Author the FR or correct the marker |

### L5 ratchet — engineer triage (1 entry)

| # | TC ID | Scope | Drift entries | Notes |
|---|---|---|---|---|
| 1 | TC-ORD-001-HP-001 | orders-t1 | drift-015 | **P0 regression**. Was green for 8 consecutive runs (`green_streak_broken` accumulator P1 attaches). Last passed 2026-04-29 nightly, failed today's PR. Implementing handler: `OrderSubmitController.handle()` (covered by `FR-ORD-001 AC-1`). Recent author: assign for triage |

### L1 PRD — informational (1 entry)

| # | PRD | Drift entries | Notes |
|---|---|---|---|
| 1 | docs/prd/orders/index.md | drift-016 | **P3** `prd_no_block` — orders PRD has no Contract Block yet. Phase 4.1 backfill candidate. Not actionable as drift unless scope is escalated |

### Waiver-eligible (1 entry — accept until 2026-05-15)

| # | FR | Drift entry | Reason | Expires |
|---|---|---|---|---|
| 1 | docs/fr/orders/fr-order-fulfill.md | drift-006 | `endpoint POST /api/v1/orders/{id}/refund` — FR ahead of code, scheduled for sprint-46 | 2026-05-15 |

---

## Detail per entry (selected — full list in JSON)

### drift-001
- **FR**: docs/fr/orders/fr-order-submit.md (covers FR-ORD-001)
- **Claim**: endpoint POST /api/v1/orders with permission `orders.submit`
- **Reality**: handler at `OrderSubmitController.java` exists but uses permission `orders.create` (mismatch)
- **Class**: Real-mismatch
- **Severity**: **P0** (permission)
- **Confidence**: high
- **Recommendation**: manual_review — decide if `orders.submit` is new permission to add (FR is right) or rename FR claim (code is right). Cross-check `OrdersPermission.java` constants and the front-end `can()` map
- **Last edit signal**: FR last edited 3 days ago, code last edited 8 weeks ago — likely FR ahead

### drift-007
- **FR**: docs/fr/orders/fr-order-submit.md
- **Claim**: AC-12 — `cancelByCustomer()` emits `audit.Log()` with action=delete
- **Reality**: `OrderSubmitService.cancelByCustomer()` has no `audit.Log()` call and no `// audit:skip` marker. Drift kind: `code_comment` reason: `marker_missing`. Method classified as B1 (FR-AC mapped) by triage helper
- **Class**: FR-ahead (code lags) — but P0 due to audit semantics
- **Severity**: **P0**
- **Confidence**: high
- **Recommendation**: night-builder — either add `audit.Log()` per FR-ORD-001 AC-12 OR add `// audit:skip — cascade emit from OrderCancelOrchestrator` if the audit emit is genuinely covered upstream

### drift-010
- **FR**: (orphan)
- **Claim**: leading comment `FR-ORD-099 AC-1` in `audit_writer.go::flushBatch()`
- **Reality**: no FR file declares FR-ORD-099 in any contract block
- **Class**: Real-mismatch (marker_orphan_fr)
- **Severity**: **P0** (orphan FR reference is structurally invalid)
- **Confidence**: high
- **Recommendation**: fr-writer — author `FR-ORD-099` (likely intended as audit batching FR) OR correct the marker if it's a typo (e.g. `FR-ORD-009`)

### drift-015 (L5 ratchet)
- **TC**: TC-ORD-001-HP-001 ("Customer submits valid cart with valid payment")
- **Scope**: orders-t1 (`docs/test-reports/_ratchet/orders-t1-state.json`)
- **History**: 8 consecutive `passed` (run-IDs in state file), latest run `failed`
- **Class**: real regression (not flake — green streak triggers)
- **Severity**: **P0**
- **Recommendation**: engineer triage. Scenario `traces_to: [FR-ORD-001 AC-1]`. Implementing handler: `OrderSubmitController.handle()` (FR-ORD-001 AC-1). Cross-check `green_streak_broken` (additive P1) — high confidence this is a real regression, not a flake. Last commit on `OrderSubmitController.java`: 4 hours ago — the most likely culprit

---

## Open questions

- drift-004 (status enum mismatch `PENDING` vs `NEW`) requires an ADR for the rename — neither side is obviously canonical. Suggest convening the orders module owner before fr-writer or night-builder is dispatched
- drift-016 (`prd_no_block`) is informational P3 but might be promoted to P1 if scope escalates to enforcing PRD blocks on all mature modules. Decision: out of scope for this triage; revisit after Phase 5 adoption

---

*Generated by drift-triager. Source JSON: `docs/drift-reports/2026-04-30/report-drift.json`. Schemas: `docs/fr/_contract-schema.json`, `docs/prd/_contract-schema.json`, `docs/test-scenarios/_contract-schema.json`, `docs/test-reports/_ratchet-schema.json`.*
