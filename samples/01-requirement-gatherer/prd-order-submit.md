# Workflow — order-submit

**Flows**: F-01 (happy path), F-02 (payment declined) · **Primary actor**: Customer

## Domains Affected

| Domain | Involvement |
|---|---|
| Catalog | Price & availability snapshot |
| Inventory | Reserve on confirm, release on cancel |
| Payment | Authorize → capture on dispatch |
| Orders | Create + state machine owner |
| Notification | Confirmation email/SMS |
| Audit | State transition log |

## Workflow Overview

**Trigger**: Customer klik "Place Order" button di checkout page.

**Actors**:
- Customer (primary) — authenticated via session token
- System (inventory, payment) — internal actors untuk reserve/authorize

**Decision Tree**:

```
1. Validate cart snapshot
   ├─ valid         → step 2
   └─ invalid       → reject with PRICE_DRIFT or SKU_UNAVAILABLE

2. Reserve inventory
   ├─ success       → step 3
   └─ out-of-stock  → reject with INSUFFICIENT_STOCK

3. Authorize payment
   ├─ success       → step 4
   └─ declined      → release inventory, reject with PAYMENT_DECLINED

4. Create order (state=PENDING)
   └─ step 5

5. Transition PENDING → CONFIRMED
   └─ dispatch async: notification + fulfillment queue
```

## Business Rules

| ID | Rule |
|---|---|
| BR-1 | Order tidak boleh dibuat jika cart price berbeda > 1% dari harga katalog saat submit (anti-tampering) |
| BR-2 | Inventory reservation berlaku 15 menit; bila payment authorize > 15 menit, reservation expired dan harus retry |
| BR-3 | Satu `Idempotency-Key` hanya boleh menghasilkan satu order dalam window 24 jam |
| BR-4 | Order > USD 1,000 wajib melewati additional fraud check (async) — state `CONFIRMED` tapi `flagged=true` |
| BR-5 | Customer maksimal 5 order PENDING concurrent — selebihnya reject dengan RATE_LIMITED |

## Compliance

- PCI DSS — card details tidak masuk ke service Orders; hanya payment token
- GDPR — order data retained 7 years untuk compliance; shipping address anonymized setelah customer account delete

## UI/UX Wireframes (text)

### Checkout → Place Order

```
┌──────────────────────────────────────────┐
│ CHECKOUT                                 │
│                                          │
│ Shipping to: [address summary]   [edit]  │
│ Payment:     [**** 4242]         [edit]  │
│                                          │
│ Subtotal:              USD 125.00        │
│ Shipping:              USD   9.99        │
│ Tax:                   USD  10.80        │
│ ──────────────────────────────────       │
│ Total:                 USD 145.79        │
│                                          │
│ [ Place Order ]  ← primary action        │
└──────────────────────────────────────────┘
```

### Confirmation

```
✓ Order #ORD-2026-00042 confirmed
  Estimated delivery: Apr 24 – Apr 26
  [View order details]
```

### Error states

- `PRICE_DRIFT` → "Price changed since you added items. Please review cart."
- `INSUFFICIENT_STOCK` → "One or more items out of stock. Cart updated."
- `PAYMENT_DECLINED` → "Payment was declined. Try a different method."

## Data Model

### Entity: Order

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| order_number | string | human-readable, format `ORD-YYYY-NNNNN` |
| customer_id | UUID | FK |
| state | enum | PENDING, CONFIRMED, PACKED, DISPATCHED, DELIVERED, CANCELLED, RETURNED |
| total_amount | decimal(12,2) | |
| currency | char(3) | ISO 4217 |
| idempotency_key | string | unique per customer per 24h |
| flagged | boolean | fraud check pending |
| created_at, updated_at | timestamp | |

### Entity: OrderItem

| Field | Type |
|---|---|
| order_id | UUID FK |
| sku | string |
| quantity | int |
| unit_price | decimal(12,2) |
| subtotal | decimal(12,2) |

## Dependencies

| Upstream | What we need |
|---|---|
| Catalog service | Real-time price lookup, availability flag |
| Inventory service | Reserve/release API with TTL support |
| Payment gateway | Authorize/capture/void/refund API |
| Fulfillment queue | Async dispatch endpoint |

## Risks & Assumptions

- **A1**: Payment gateway latency P95 ≤ 1s. Assumption berdasarkan observed metric vendor. Jika > 2s, user perception broken → risk redesign confirmation UX.
- **R1**: Inventory race — dua customer submit simultan untuk last stock. Mitigasi: optimistic locking di Inventory service.
- **A2**: Idempotency-Key client-generated (bukan server) — client library menjamin uniqueness. Risk: naive client duplicate orders.

## References

- Flow map: `docs/prd/orders/index.md#flow-map`
- FR output: `docs/fr/orders/fr-order-submit.md` *(to be generated)*
