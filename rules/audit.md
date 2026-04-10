# Audit Rules

## Core Principle
Explicit audit — setiap CUD operation wajib panggil `audit.Log()` secara sadar di service layer. Tidak ada middleware magic. Developer bertanggung jawab penuh.

## Rules

1. **Setiap CUD wajib `audit.Log()` atau `// audit:skip`**
   - Create, Update, Delete di service method harus ada `audit.Log()`
   - Kalau sengaja tidak audit, tulis `// audit:skip — <alasan>`
   - CUD tanpa keduanya = flag saat review

2. **Read tidak di-audit by default**
   - Hanya audit read kalau explicitly diminta

3. **Context carry actor info**
   - `ctx` harus sudah berisi: user_id, ip, request_id, user_agent
   - Diset sekali di auth middleware, `audit.Log()` baca dari ctx

4. **Update/Delete wajib capture before state**
   - Fetch data sebelum mutasi, pass sebagai `Before` di audit event

5. **Approval workflow wajib log transition**
   - from_status, to_status, actor, comment, timestamp
   - Setiap state change = 1 audit entry

6. **Async & non-blocking**
   - `audit.Log()` publish event ke message bus
   - Tidak boleh blocking business logic
   - Flow: `audit.Log()` → Message Bus → Audit Consumer → NoSQL Storage

7. **Audit data immutable**
   - Storage tidak boleh support update/delete audit records
   - Retention & archiving strategy terpisah

8. **Storage independent dari app DB**
   - Audit disimpan di NoSQL (MongoDB/Elasticsearch) terpisah dari transactional DB
   - Tidak tergantung stack app

## Event Schema

```json
{
  "event_id": "uuid",
  "timestamp": "RFC3339",
  "actor": {
    "user_id": "uuid",
    "ip": "string",
    "user_agent": "string",
    "request_id": "uuid"
  },
  "action": "create|update|delete|approval_transition",
  "resource": {
    "type": "entity name",
    "id": "uuid",
    "namespace": "service name"
  },
  "payload": {
    "before": {},
    "after": {}
  },
  "metadata": {
    "tags": ["financial", "pii"],
    "source": "api|system|scheduler"
  }
}
```

## Code Pattern

```go
// Standard CUD
audit.Log(ctx, audit.Event{
    Action:   audit.Create,
    Resource: audit.Resource{Type: "order", ID: order.ID},
    Before:   nil,
    After:    order,
})

// Approval transition
audit.Log(ctx, audit.Event{
    Action:   audit.ApprovalTransition,
    Resource: audit.Resource{Type: "purchase_request", ID: pr.ID},
    Before:   audit.Status{From: "pending"},
    After:    audit.Status{To: "approved"},
    Meta:     map[string]any{"comment": "Budget verified", "step": 2},
})

// Explicit skip
// audit:skip — internal cache, no business impact
```

## Review Checklist
- [ ] Semua CUD punya `audit.Log()` atau `// audit:skip`?
- [ ] Update/Delete capture before state?
- [ ] Approval transition log from/to + comment?
- [ ] `audit.Log()` async (non-blocking)?
- [ ] Tidak ada update/delete ke audit storage?
