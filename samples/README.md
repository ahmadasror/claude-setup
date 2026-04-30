# Agent Pipeline — Sample Outputs

Sample artefak per agent di pipeline, menggunakan running example:
- **Module**: `orders`
- **Workflow**: `order-submit`
- **Actors**: Customer, Fulfillment Operator
- **Domain**: e-commerce (generic)

Semua nama, angka, kredensial, dan ID di sini **fictional** — dipakai hanya untuk menunjukkan struktur output yang diharapkan per agent. Saat menjalankan agent di project asli, output akan menyesuaikan konteks project.

**Multi-language by design**: night-builder sample membuat Java (`orders-service/src/main/java`), test-builder sample membuat TypeScript (Playwright). Ini mencerminkan shape project realistis — backend monolith + frontend SPA + E2E suite. Agent tidak bias ke satu stack; mereka mengikuti konvensi project yang dijalankan.

**Placeholder dates**: semua tanggal di sample file (`2026-04-20`, `ORD-2026-NNNNN`, dll) di-freeze ke tanggal generation. Saat dipakai sebagai template, replace dengan tanggal run aktual.

## Urutan

| # | Agent | Folder | Menghasilkan |
|---|---|---|---|
| 1 | requirement-gatherer | `01-requirement-gatherer/` | PRD (index + per-workflow) |
| 2 | architect | `02-architect/` | design.md + ADR |
| 3 | fr-writer | `03-fr-writer/` | FR index + fr-workflow + completion-status |
| 4 | tester-explorer | `04-tester-explorer/` | Test scenario doc (3 phases) |
| 5 | test-builder | `05-test-builder/` | Playwright specs + test report |
| 6 | night-builder | `06-night-builder/` | Night build report |
| 7 | pimpro | `07-pimpro/` | Pipeline status dashboard |
| 8 | drift-triager | `08-drift-triager/` | Drift triage report (post-drift detector run) |

## Baca urutannya

PRD → design.md → FR → test scenarios → Playwright specs → night-build report → status dashboard. Tiap dokumen mereferensikan upstream-nya (FR refer ke PRD F-NN, test scenarios refer ke FR AC-IDs, dll).

## Cara dipakai

- **Template**: copy sebagai starting skeleton, ganti isi dengan konteks project asli.
- **Reference shape**: ketika agent output tidak sesuai ekspektasi, compare dengan sample di sini untuk identifikasi section yang miss.
- **Onboarding**: collaborator baru bisa baca samples berurutan untuk memahami flow pipeline tanpa perlu project asli.
