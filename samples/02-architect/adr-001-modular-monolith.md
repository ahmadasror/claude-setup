# ADR-001 — Modular Monolith for Orders Module v1

**Status**: Accepted · **Date**: 2026-04-20 · **Deciders**: architect agent + {tech lead}

## Context

Orders module perlu mengorkestrasi 5 domain (Catalog, Inventory, Payment, Fulfillment, Notification). Pilihan arsitektur berkisar:

1. **Microservices per domain** — setiap domain service independent
2. **Modular monolith** — satu deployable, tapi domain-module terisolasi dengan ports & adapters
3. **Event-driven choreography** — no central orchestrator, domains react to events

## Decision

Pilih **modular monolith** (option 2) untuk v1.

## Rationale

| Aspek | Monolith modular | Microservices | Event choreography |
|---|---|---|---|
| Time to ship v1 | ✓ Fastest | ✗ 3x setup | ✗ Choreography reasoning hard |
| Operational cost | ✓ 1 deploy, 1 DB | ✗ 5 services, service mesh | ✗ Broker + dead letter ops |
| Transaction boundary | ✓ Local TX | ✗ Saga complexity | ✗ Saga + eventual consistency debug |
| Future refactor | ✓ Module → service later | n/a | ✗ Hard to unwind |
| Team size fit | ✓ Team of 4-8 | ✗ Needs > 15 for sane split | ✗ Advanced team only |

Kondisi saat ini: tim 6 engineer, satu product, butuh ship cepat. Microservice premature. Event choreography premature. Monolith modular menyimpan optionality untuk extract ke service bila scale demand.

## Consequences

**Positive**
- Single transaction boundary untuk order → payment → inventory (via outbox pattern untuk async dispatch)
- Deployment sederhana: 1 CI pipeline, 1 artifact
- Local dev mudah — bisa jalan tanpa docker-compose multi-service

**Negative**
- Risk "big ball of mud" kalau module boundaries tidak di-enforce — mitigation: ArchUnit test di CI
- Scaling kasar — harus scale seluruh app meskipun cuma Orders yang hot

**Neutral**
- Migration path ke microservice butuh API-first design dari hari pertama — sudah direncanakan di design.md

## Compliance Guardrails

- Module-to-module communication **harus** via Application Service interface — tidak boleh cross-module DB access
- Domain events published via outbox table — event bus swap nanti non-breaking
- ArchUnit test: no package cross-dependency violation, wajib green di CI

## References

- Design: `docs/architecture/orders/design.md`
- Follow-up ADRs: ADR-002 (saga compensation), ADR-003 (read model — TBD)
