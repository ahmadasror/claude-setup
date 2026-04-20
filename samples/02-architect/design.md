# Architecture — Orders Module

**Status**: Baseline · **Generated**: 2026-04-20 by architect · **Version**: 1.0

## Context

Orders module adalah aggregate root untuk siklus order. Ia mengorkestrasi 3 service upstream (Catalog, Inventory, Payment) dan 2 downstream (Fulfillment, Notification). Arsitektur ini di-derive langsung dari PRD — tidak perlu menunggu FR.

## Architectural Style

- **Service**: Modular monolith dengan domain boundaries jelas (Hexagonal Ports & Adapters)
- **Persistence**: PostgreSQL untuk transactional state, Redis untuk idempotency cache & reservation TTL
- **Messaging**: RabbitMQ untuk async dispatch ke Fulfillment + Notification (at-least-once)
- **Read models**: Eventual consistency via domain events (no CQRS read-side yet — v2 if traffic demands)

## Component Map

```
                     ┌─────────────────────────────────────┐
                     │  API Gateway / Edge                 │
                     └────────────────┬────────────────────┘
                                      │
                     ┌────────────────▼────────────────────┐
                     │  Orders Service (monolith)          │
                     │                                     │
                     │  ┌──────────────────────────────┐   │
                     │  │ REST Controller              │   │
                     │  └──────────┬───────────────────┘   │
                     │             ▼                       │
                     │  ┌──────────────────────────────┐   │
                     │  │ Application Service          │   │
                     │  │ (OrderSubmitService, etc.)   │   │
                     │  └───┬────────┬────────┬────────┘   │
                     │      ▼        ▼        ▼            │
                     │  ┌─────┐  ┌─────┐  ┌──────────┐     │
                     │  │ Dom │  │ Dom │  │ Outbound │     │
                     │  │ ain │  │ ain │  │ Ports    │     │
                     │  └──┬──┘  └──┬──┘  └────┬─────┘     │
                     └─────┼────────┼──────────┼───────────┘
                           ▼        ▼          ▼
                     ┌─────────┐ ┌──────┐ ┌─────────────────────┐
                     │ Postgres│ │ Redis│ │ Outbound Adapters   │
                     │ (orders │ │ (idem│ │ Catalog / Inventory │
                     │  orderI │ │  cache│ │ Payment / Fulfill  │
                     │  tems)  │ │  resv)│ │ Notification       │
                     └─────────┘ └──────┘ └─────────────────────┘
```

## API Contract (initial)

### POST /api/v1/orders

**Request**
```json
{
  "cart_snapshot": {
    "items": [
      { "sku": "SKU-ABC-001", "quantity": 2, "unit_price": 25.00 }
    ],
    "total": 145.79
  },
  "payment_token": "tok_...",
  "shipping_address_id": "uuid"
}
```
Headers: `Idempotency-Key: <uuid>` (required)

**Response — 201 Created**
```json
{
  "order_id": "uuid",
  "order_number": "ORD-2026-00042",
  "state": "CONFIRMED",
  "total_amount": 145.79,
  "currency": "USD",
  "flagged": false,
  "created_at": "2026-04-20T10:15:00Z"
}
```

### Error Response Envelope

```json
{
  "code": "<ERROR_CODE>",
  "message": "<human-readable>",
  "trace_id": "<X-Request-ID>",
  "details": { }
}
```

### Error Code Table (initial — fr-writer will expand)

| Code | HTTP | Trigger |
|---|---|---|
| PRICE_DRIFT | 409 | Cart price berbeda > 1% dari katalog |
| SKU_UNAVAILABLE | 410 | SKU deactivated di katalog |
| INSUFFICIENT_STOCK | 409 | Reservation gagal — stok kurang |
| PAYMENT_DECLINED | 402 | Gateway decline |
| DUPLICATE_ORDER | 409 | Idempotency-Key match existing order |
| RATE_LIMITED | 429 | > 5 PENDING concurrent per customer |

## Data Model

(Referensi PRD §Data Model — di sini arsitektur menambahkan index & constraint.)

### Indexes
- `orders(customer_id, state)` — list customer orders by state
- `orders(idempotency_key)` UNIQUE — dedup enforcement
- `orders(order_number)` UNIQUE
- `order_items(order_id)` — FK lookup

### Constraints
- `orders.state` enum constraint (DB-level check)
- `orders.total_amount >= 0`
- FK `order_items.order_id → orders.id` ON DELETE CASCADE

## State Machine

```
PENDING ─────┬──► CONFIRMED ─────► PACKED ─────► DISPATCHED ─────► DELIVERED
             │                │                    │                  │
             └──► CANCELLED   └──► CANCELLED       └──► CANCELLED    └──► RETURNED
              (timeout)        (customer cancel)    (ops cancel)       (RMA flow)
```

State transitions are append-only in `order_state_history` table — source of truth untuk audit.

## Concurrency & Consistency

| Scenario | Strategy |
|---|---|
| Inventory race (last stock) | Optimistic lock di Inventory service + reservation TTL |
| Idempotency duplicate submit | Redis SETNX keyed by `Idempotency-Key` + customer_id, 24h TTL |
| Payment authorize timeout | Saga compensation — release inventory bila payment gagal/timeout |
| Concurrent state transitions | Row-level pessimistic lock (`SELECT ... FOR UPDATE`) pada orders row |

## Observability

- **Metrics**: submit latency histogram, error rate by code, state transition rate
- **Logs**: structured JSON, `X-Request-ID` propagated to upstream calls
- **Traces**: OpenTelemetry spans — submit → inventory.reserve → payment.authorize → order.persist
- **Alerts**: P95 latency > 3s (5min), error rate > 2% (5min), inventory reserve fail rate > 5%

## Security

- Auth: session token via `Authorization: Bearer <jwt>`
- PCI: card never touches Orders service — only payment token
- PII: shipping address encrypted at rest (column-level), TLS in transit
- Rate limit: 20 req/min per customer at edge

## NFR Mapping

| NFR | Design choice |
|---|---|
| ≤ 3s P95 confirmation | Async dispatch (fulfillment + notification) selepas CONFIRMED; kritikal path hanya reserve + authorize + persist |
| 200/min sustained | Connection pool sized 50, Redis keluar critical path reservation |
| 99.9% availability | Active-passive DB failover, stateless app instances behind LB |
| Idempotency 24h | Redis `Idempotency-Key` TTL |
| Audit retention 7y | Separate audit storage (append-only), partitioned by year |

## ADRs

Keputusan arsitektural dicatat di ADR terpisah:
- ADR-001 — Monolith vs microservice pilihan (lihat `adr-001-modular-monolith.md`)

## Conformity Checkpoint Notes

Tidak ada kode yang perlu dicek pada initial run — FR dan implementasi belum ada. Setelah implementasi pertama merged, architect akan di-invoke lagi sebagai conformity checkpoint untuk deteksi drift.

## References

- PRD: `docs/prd/orders/`
- Discovery: `docs/discovery/2026-04-12-order-abandonment.md`
- Domain map: `docs/architecture/domains/index.md`
- FR (downstream): `docs/fr/orders/` *(to be generated)*
