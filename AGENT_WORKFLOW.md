# Agent Workflow

Panduan agent pipeline: urutan eksekusi, input/output tiap agent, dan siapa yang mengkonsumsi hasilnya. Template reusable — project-level infra (scripts, runbooks, Makefile targets) disetup terpisah per project.

---

## Pipeline Utama: Discovery → Build → Test → Supervise

```
requirement-gatherer
        │
        ├─ docs/prd/{module}/
        └─ docs/architecture/domains/
                │
                ▼
           architect  ← wajib minimal sekali per modul
                │
                ├─ docs/architecture/{module}/design.md
                └─ docs/architecture/adr/
                        │
                        ▼
                   fr-writer
                        │
                        └─ docs/fr/{module}/
                                │
                         ┌──────┴──────┐
                         ▼             ▼
                  tester-explorer   night-builder
                         │          (implementasi: source code + Java unit tests)
                         │                │
                  docs/test-scenarios/    ▼
                         │          architect ← conformity checkpoint
                         ▼          (berkala, per sprint/milestone)
                   test-builder          │
                   (Playwright:     drift? ──YES──→ fr-writer (update FR)
                    generate +           │                  │
                    run + report)        NO         tester-explorer (update scenarios)
                         │
                  docs/test-reports/
                         │
                         └──────────────────────────┐
                                                     ▼
                                               pimpro ← supervisi pipeline
                                               (baca: FR status + artifact existence
                                                + night-build reports + test reports)
```

**Aturan urutan:**
1. `requirement-gatherer` harus selesai dulu — PRD adalah input architect
2. `architect` wajib dijalankan minimal sekali sebelum `fr-writer` — API contracts dan data model dari architect adalah input fr-writer untuk generate response codes dan AC yang akurat
3. `tester-explorer` dan `night-builder` berjalan dari FR — bisa paralel setelah FR selesai
4. `test-builder` berjalan setelah `tester-explorer` Phase 3 selesai — generate Playwright files, run, tulis report
5. Setelah implementasi berjalan, `architect` dijalankan kembali sebagai **conformity checkpoint** — membandingkan kode dengan `design.md`, melaporkan drift, membuat ADR baru bila ada keputusan yang belum terdokumentasi
6. Jika conformity checkpoint menemukan drift signifikan → **loop ke fr-writer** untuk update FR yang terpengaruh, lalu tester-explorer untuk update test scenarios
7. `night-builder` membaca FR + architecture + codebase — bukan hanya FR

**Error traceability:**
- Playwright inject `X-Request-ID: pw-{id}` di setiap request
- Kalau test gagal: `docker logs {service-name} 2>&1 | grep "<RUN_ID>"`
- Log management: stdout Docker umumnya cukup untuk project kecil/menengah. Opsi self-host ringan: **Seq** (1 container, ~200MB) — search log via UI, filter by request ID

---

## Cross-Agent Contract — UI Selectors

> Contract ini muncul dari insiden di mana test assertion memakai `data-testid` yang tidak sama dengan yang diimplementasikan di template — test pass, padahal elemen tidak pernah match. Sejak itu, testid ditetapkan di FR dulu sebelum implementasi dan test code lahir.
> **Spec lengkap** (per project): `docs/architecture/testing/ui-selector-contract.md`

### Prinsip

`data-testid` adalah **published API** yang mengikat 4 agent (fr-writer, night-builder, tester-explorer, test-builder). Nilainya disepakati di FR **sebelum** implementasi UI atau test code lahir — bukan ditemukan post-hoc dari kode. Rename = perlu FR update, bukan silent edit.

### Alur

```
fr-writer  ─── Produces ───▶  ## UI Selectors section di FR file
                             (kolom: testid | Page | Component | Role | AC)
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            night-builder      tester-explorer      test-builder
            (implements        (Phase 3 extracts    (Playwright uses
             verbatim)          testid dari FR;      testid dari FR;
                                block kalau absen)   tidak boleh invent)
                    │                  │                  │
                    └──────────────────┴──────────────────┘
                                       ▼
                           scripts/build-ui-selector-registry.sh
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
           docs/fr/ui-selector-registry.md   docs/fr/ui-selector-registry.json
           (human-readable aggregate)        (machine-readable; consumed
                                              oleh smoke spec)
                                       │
                                       ▼
                     e2e/tests/contract/ui-selectors.spec.ts
                     (CI gate — block main suite kalau testid missing)
```

### Tanggung jawab per agent

| Agent | Kewajiban terkait UI Selectors |
|---|---|
| **fr-writer** | Wajib menulis `## UI Selectors` section di setiap FR dengan UI surface. Satu row per stable element. Kolom: `testid \| Page \| Component \| Role \| AC`. Naming: lowercase kebab-case dengan prefix peran (lihat contract §Naming rules). |
| **night-builder** | Implementasi testid **persis** seperti di FR. Jangan invent, jangan rename. Testid absent di FR = stop + log HIGH assumption proposing row baru ke FR, bukan invent di template. |
| **tester-explorer** | Phase 2 checkpoint: verifikasi setiap page yang flow-nya kunjungi punya `## UI Selectors` section lengkap. Kalau absen atau incomplete → flag sebagai `MISSING — UI Selectors` dan **block Phase 3** untuk flow tersebut. |
| **test-builder** | Konsumsi testid dari FR saja. Setiap `page.getByTestId(...)` harus ada row di FR. Dilarang invent "probably-this-one" testid inline di spec. |

### Enforcement layers

1. **FR review** — section wajib ada sebelum night-builder diizinkan mulai.
2. **Phase 2 checkpoint** (tester-explorer) — block generation kalau testid contract tidak lengkap.
3. **Registry aggregator** — `bash scripts/build-ui-selector-registry.sh` regenerate aggregate (md + json) dari semua FR. Jalankan setelah FR diupdate.
4. **Smoke spec** — `e2e/tests/contract/ui-selectors.spec.ts` load registry JSON, login per role, navigate per page, assert `getByTestId` present. Gagal di sini = blok main Playwright run.

### Naming (ringkas — detail di contract doc)

| Prefix | Contoh | Peran |
|---|---|---|
| `{domain}-{action}-btn` | `submit-review-btn` | Button action |
| `{action}-{entity}-dialog` | `confirm-transition-dialog` | Modal/dialog root (portaled) |
| `{entity}-{field}-input` | `period-year-input` | Input field |
| `{entity}-{field}-select` | `period-month-select` | Dropdown |
| `{domain}-{role}` | `summary-gross`, `summary-net` | StatCard value |
| `{entity}-table` | `payroll-results-table` | DataTable |

### Anti-patterns (auto-reject di review)

- Invent testid di spec: `page.getByTestId('probably-this-one')`
- Rename testid untuk "lebih bagus" — renames break every consumer
- Embed UUID atau state di testid: `calculate-payroll-btn-disabled` (state properti, bukan identity)
- Chain `getByTestId(dialog).getByRole(button)` untuk portaled dialog — gunakan helper project (misal `e2e/helpers/portal-dialog.ts`) yang unwrap portal dulu.

---

## Agent 1 — requirement-gatherer

**Model**: Opus | **Kapan**: Modul baru atau modul tanpa PRD

### Input
- User intent (aspiration, UVP, positioning)
- Existing docs di `docs/` bila sudah ada
- `CLAUDE.md` untuk project context

### Output

| Artifact | Path | Sifat |
|---|---|---|
| Discovery journal | `docs/discovery/{date}-{topic}.md` | Append-only |
| Domain map | `docs/architecture/domains/index.md` | Living doc |
| PRD index | `docs/prd/{module}/index.md` | Per modul |
| PRD per-workflow | `docs/prd/{module}/{workflow}.md` | Per workflow |

### Struktur PRD index
- Executive summary
- Personas
- Domains Affected (table: domain / read-write / operations)
- **Flow Map** — satu block per end-to-end business process (Trigger, Actor, Outcome, Prerequisite, Business steps, PRD workflows)
- **Workflow File Map** — tabel mapping file workflow ke FRs dan domain
- NFR summary
- References (link ke discovery, domain map, FR layer)

> Flow Map adalah kontrak antara PRD dan FR layer. fr-writer membacanya dan menambahkan FR refs, ticket refs, dan test scenario links ke tiap flow block.

### Flow Map vs PRD Workflows — perbedaan

Keduanya ada di PRD tapi menjawab pertanyaan berbeda:

| | Flow Map (F-NN) | PRD Workflows |
|---|---|---|
| **Perspektif** | User journey — satu user goal selesai | Functional capability — apa yang sistem bisa lakukan |
| **Unit** | End-to-end business process | Satu domain/kapabilitas fungsional |
| **Isi** | Trigger, Actor, Outcome, Prerequisite, Business steps | Business rules detail, state machine, data model, validation |
| **Granularitas** | Coarse — "apa yang user capai" | Fine — "bagaimana sistem melakukannya" |

Hubungannya **many-to-many** — satu flow menyentuh banyak workflow, satu workflow dipakai banyak flow:

```
F-01 ({flow-name-A}) ──── {workflow-1}
                       ├── {workflow-2}
                       ├── {workflow-3}
                       └── {workflow-4}

F-02 ({flow-name-B}) ──── {workflow-1}      (shared dengan F-01)
                       ├── {workflow-5}
                       └── {workflow-3}     (shared dengan F-01)
```

**Flow Map** menjawab *"user mau apa?"*  
**PRD Workflows** menjawab *"sistem ngapain?"*

Flow Map adalah navigation layer — baca flow map dulu untuk orientasi, baru masuk ke workflow file untuk detail implementasi.

### Struktur PRD per-workflow
1. Domains Affected (subset yang relevan)
2. Workflow overview (trigger, actors, decision tree)
3. Business rules & compliance
4. UI/UX wireframes (text-based)
5. Data model (entities, key fields)
6. Dependencies
7. Risks & Assumptions

### Dikonsumsi oleh
- **fr-writer** — membaca PRD sebagai input utama
- **architect** — membaca domain map untuk system design
- **tester-explorer** — membaca PRD sebagai Layer 1

### Handoff
Selesai di PRD. Tidak menyentuh kode. Bilang ke user untuk jalankan `fr-writer` selanjutnya.

---

## Agent 2 — architect

**Model**: Opus | **Kapan**: Wajib dijalankan minimal sekali setelah requirement-gatherer selesai per modul, sebelum fr-writer dimulai.

### Kapan dijalankan

| Mode | Trigger | Frekuensi |
|---|---|---|
| **Initial run** | requirement-gatherer selesai PRD modul baru | Wajib, sekali per modul |
| **Conformity checkpoint** | Setelah implementasi berjalan — cek apakah kode sesuai arsitektur | Berkala: per sprint atau per milestone |

**Initial run** menghasilkan architecture doc dan ADRs yang menjadi input fr-writer.

**Conformity checkpoint** tidak menghasilkan doc baru — membaca kode yang ada, membandingkan dengan `docs/architecture/{module}/design.md`, dan melaporkan drift: apa yang sudah sesuai, apa yang menyimpang, apa yang perlu ADR baru.

### Input — Initial run
- PRD: `docs/prd/{module}/` — cukup untuk menghasilkan API spec
- Discovery docs: `docs/discovery/` — konteks dan constraints
- Existing codebase — patterns yang sudah ada

> FR **belum ada** saat initial run — architect tidak perlu dan tidak boleh menunggu FR. PRD sudah cukup: workflow steps → endpoints, state machine → error codes, business rules → validation, actors → auth, NFR → constraints.

### Input — Conformity checkpoint
- Architecture doc: `docs/architecture/{module}/design.md` — baseline
- FR: `docs/fr/{module}/` — verifikasi response codes konsisten dengan implementasi
- Codebase — controller + service untuk deteksi drift

### Output

| Artifact | Path | Mode |
|---|---|---|
| Architecture doc | `docs/architecture/{module}/design.md` | Initial run |
| ADRs | `docs/architecture/adr/{NNN}-{title}.md` | Initial run + setiap keputusan baru |
| Conformity report | conversation (tidak disimpan ke file) | Checkpoint |

### Dikonsumsi oleh
- **fr-writer** — membaca API contracts dan data model untuk generate AC + response codes

---

## Agent 3 — fr-writer

**Model**: Opus | **Kapan**: Setelah PRD (dan optionally architecture) tersedia

### Input
- PRD: `docs/prd/{module}/` — workflows, business rules, NFR, out-of-scope
- Architecture: `docs/architecture/{module}/` — API contracts, data model, error codes, ADRs
- Bila architecture belum ada: fr-writer akan flag gaps, generate semaksimal mungkin

### Output

| Artifact | Path | Isi |
|---|---|---|
| FR index | `docs/fr/{module}/index.md` | Epic breakdown, flow map, ticket index |
| FR per-workflow | `docs/fr/{module}/fr-{workflow}.md` | Epics, ticket stubs, AC tables, response codes, **`## UI Selectors` section** (wajib bila FR punya UI surface) |
| Completion status | `docs/fr/{module}/completion-status.md` | Open questions, assumed decisions, build order |

### Struktur ticket stub
```
### T-{N}: {title}
Epic: {epic-name}
Domain: {domain}
Type: Story | Task | Spike
Size: S | M | L | XL

Acceptance Criteria:
- {condition} → {expected outcome}
- {error condition} → {HTTP code + error code}
- {NFR condition} → e.g. "response < 500ms P99"

Notes: {implementation context non-obvious}
```

### Dikonsumsi oleh
- **tester-explorer** — membaca FR sebagai Layer 2 (AC + response code baseline)
- **Engineers** — membaca ticket stubs sebagai work items
- **night-builder** — membaca FR + scenarios untuk autonomous implementation

---

## Agent 4 — tester-explorer

**Model**: Opus | **Kapan**: Setelah FR tersedia

### Input
- PRD: `docs/prd/{module}/` (Layer 1 — state machine, business rules)
- FR: `docs/fr/{module}/` (Layer 2 — AC, response codes)

### Output

Single progressive file, 3 phases:

| Phase | Isi | Path |
|---|---|---|
| Phase 1 | Workflow, state machine, BR inventory, AC log | `docs/test-scenarios/{module}/tester-{domain}-{date}.md` |
| Phase 2 | Seed data map, precondition templates | Append ke file Phase 1 |
| Phase 3 | Test scenarios (kategorisasi), coverage matrix, gaps | Append ke file Phase 1 |

### Kategori test scenario
`HP` Happy Path · `SP` Sad Path · `ST` State Transition Valid · `STX` State Transition Invalid · `BR` Business Rule · `AUTH` Authorization · `IDEM` Idempotency · `CONC` Concurrency · `EDGE` Boundary · `INT` Integration · `AUDIT` Audit Trail · `COMP` Rollback/Compensation

### Dikonsumsi oleh
- **QA** — manual testing dari Phase 3 scenarios
- **night-builder** — automated test implementation
- **Engineers** — referensi edge cases saat build

---

## Agent 5 — test-builder

**Model**: Opus | **Kapan**: Setelah tester-explorer Phase 3 selesai — generate, run, dan report Playwright tests

### Input
- Test scenarios: `docs/test-scenarios/{module}/api/flow-NN-*.md` (API TCs)
- Test scenarios: `docs/test-scenarios/{module}/fe/flow-NN-*.md` (FE TCs)
- `CLAUDE.md` untuk credentials, API envelope, service URLs
- Existing `e2e/tests/{module}/` untuk pattern reference

### Output
- `e2e/tests/{module}/{module}-flow{NN}-api.spec.ts` — Playwright APIRequestContext (API layer)
- `e2e/tests/{module}/{module}-flow{NN}-{name}.spec.ts` — Playwright browser E2E (FE layer)
- Run: `npx playwright test tests/{module}/ --reporter=list,'json:.pw-results.json'`
- Report: `docs/test-reports/{date}-{module}-report.md` via `node e2e/scripts/gen-report.js`

### Batasan
- **Tidak menyentuh source code** — hanya baca test scenarios, tulis test files
- **Tidak generate Java tests** — Java unit/controller test tanggung jawab night-builder
- **`data-testid` dari FR, bukan tebak** — setiap `page.getByTestId(...)` harus ada row di `## UI Selectors` section FR. Lihat Cross-Agent Contract — UI Selectors di atas.
- `test.fixme()` untuk TC yang butuh seed state di luar default seed
- `X-Request-ID: pw-{id}` di-inject ke semua requests untuk error traceability

### Re-run (engineer / CI)
```bash
make test-{module}-e2e   # re-run semua E2E modul + regenerate report
```
`make test-{module}-e2e` bukan output test-builder — ini shortcut project-level untuk engineer/CI re-run kapan saja. test-builder jalankan Playwright langsung saat generate.

---

## Agent 6 — night-builder

**Model**: Opus | **Kapan**: Autonomous overnight implementation

### Input
- FR: `docs/fr/{module}/`
- Architecture: `docs/architecture/{module}/design.md`
- Test scenarios: `docs/test-scenarios/{module}/`
- Codebase (read + write)

### Output
- Code implementation (source code + Java unit/controller tests)
- Report: `docs/night-builds/{date}-{topic}-report.md`

---

## Agent Contract Table

| Agent | Input | Produces | Dikonsumsi oleh |
|---|---|---|---|
| **requirement-gatherer** | User intent · `docs/` existing · `CLAUDE.md` | `docs/discovery/` · `docs/architecture/domains/` · `docs/prd/{module}/` | architect · fr-writer · tester-explorer |
| **architect** *(initial)* | `docs/prd/{module}/` · `docs/discovery/` · codebase | `docs/architecture/{module}/design.md` · `docs/architecture/adr/` | fr-writer |
| **architect** *(checkpoint)* | `docs/architecture/{module}/design.md` · `docs/fr/{module}/` · codebase | Conformity report (conversation) · ADR baru bila drift | fr-writer (bila drift) · pimpro |
| **fr-writer** | `docs/prd/{module}/` · `docs/architecture/{module}/design.md` | `docs/fr/{module}/index.md` · `docs/fr/{module}/fr-{workflow}.md` (incl. `## UI Selectors`) · `docs/fr/{module}/completion-status.md` | tester-explorer · engineers · night-builder · test-builder · pimpro |
| **tester-explorer** | `docs/prd/{module}/` · `docs/fr/{module}/` · seed data | `docs/test-scenarios/{module}/` (3 phases) | QA · test-builder · night-builder · engineers · pimpro |
| **test-builder** | `docs/test-scenarios/{module}/api+fe/` · `CLAUDE.md` | `e2e/tests/{module}/*.spec.ts` · `docs/test-reports/{date}-report.md` | QA · engineers · pimpro |
| **night-builder** | `docs/fr/{module}/` · `docs/architecture/{module}/design.md` · codebase | Source code + Java unit tests · `docs/night-builds/{date}-report.md` | pimpro |
| **pimpro** | `docs/fr/status.md` · artifact existence · status headers · night-build reports · test reports | `docs/pimpro/status-{date}.md` — pipeline dashboard + next action per modul | User / project owner |

---

## Agent 7 — pimpro *(supervisor)*

**Model**: Sonnet | **Kapan**: Otomatis setelah setiap pipeline agent selesai

### Prinsip
- **Agregat status saja** — baca sinyal yang di-report agent lain, bukan analisis konten
- **High-level** — satu baris per modul, bukan per artifact detail
- **Recommend, don't trigger** — usulkan next action ke user, tidak invoke agent lain
- **Own workspace only** — hanya boleh tulis ke `docs/pimpro/`
- **DoR/DoD bukan urusan pimpro** — masing-masing agent bertanggung jawab atas conformity dan violations-nya sendiri

### Input (sinyal status, bukan konten)
- `docs/fr/status.md` — canonical status tracker
- Existence check per artifact per modul (`index.md` ada atau tidak)
- Status header 20 baris pertama tiap file (self-reported by each agent)
- Night-builder reports: `docs/night-builds/` — summary section saja
- Test reports: `docs/test-reports/` — pass/fail/skip counts per modul

### Output

| Artifact | Path | Sifat |
|---|---|---|
| Status dashboard | `docs/pimpro/status-{date}.md` | Overwrite harian |

### Dikonsumsi oleh
- **User / project owner** — membaca status report dan rekomendasi

---

## Agent Pendukung (non-pipeline)

| Agent | Kapan dipakai | Output |
|---|---|---|
| `go-reviewer` | Code review Go — sebelum merge | Review comments |
| `security-reviewer` | Security audit — sebelum release | Security findings |
| `tdd-guide` | Guidance TDD workflow | Step-by-step guide |
| `planner` | Planning implementasi fitur spesifik | Implementation plan |
| `doc-tidier` | Audit & restrukturisasi docs | Restructured docs |
| `presenter` | Slide deck manajemen | HTML presentation |
| `architect-corebanking` | Core banking architecture (ledger, settlement, compliance) | Architecture review |
| `architect-financial` | Review arsitektur financial-grade | Architecture review |

---

## Quick Reference: Jalankan Agent

```bash
# Discovery modul baru
# Invoke: requirement-gatherer
# Prompt: "Buat PRD untuk modul {module-name}"

# Architecture review (wajib sebelum fr-writer, minimal sekali per modul)
# Invoke: architect
# Prompt: "Review architecture untuk modul {module-name} dari docs/prd/{module-name}/"

# FR dari PRD yang sudah ada
# Invoke: fr-writer
# Prompt: "Buat FR untuk modul {module-name} dari docs/prd/{module-name}/"

# Test scenarios dari FR
# Invoke: tester-explorer
# Prompt: "Explore domain {module-name}"

# Generate Playwright test code dari test scenarios
# Invoke: test-builder
# Prompt: "Build {module} F-01..F-N, all flows"
# Prompt: "Build {module} F-01 only"

# Autonomous build overnight (source code + unit tests)
# Invoke: night-builder
# Prompt: "Implement {FR-IDs} dari docs/fr/{module}/fr-{workflow}.md"

# Project status dashboard
# Invoke: pimpro
# Prompt: "Generate status report"
```

### Supporting agents (non-pipeline)

```bash
# Core banking architecture review (ledger, settlement, compliance)
# Invoke: architect-corebanking
# Prompt: "Review arsitektur {module} dari perspektif ledger integrity + settlement"

# Financial-grade forensic audit review
# Invoke: architect-financial
# Prompt: "Audit {module} untuk idempotency + immutable ledger compliance"

# Go code quality review
# Invoke: go-reviewer
# Prompt: "Review {service-path}/ untuk quality + best practices"

# Security vulnerability review
# Invoke: security-reviewer
# Prompt: "Audit {service-path}/ untuk OWASP Top 10"

# TDD workflow guidance
# Invoke: tdd-guide
# Prompt: "Guide TDD for implementing {feature}"

# Implementation planning (feature-specific strategy)
# Invoke: planner
# Prompt: "Plan implementation for {FR-ID} dari docs/fr/{module}/"

# Documentation audit & restructure
# Invoke: doc-tidier
# Prompt: "Audit docs/ + Confluence, propose restructure"

# HTML slide deck (management-level)
# Invoke: presenter
# Prompt: "Generate deck for {topic}, target audience: management"
```

---

## AI Discovery — Helper Scripts vs Re-Discovery

**Prinsip:** setiap operasi yang AI pernah debug & solve harus jadi **helper script di `scripts/`** + **runbook di `docs/ops/{runbooks,testing}/`** + **referensi di `CLAUDE.md`**. Tujuannya: sesi berikutnya AI cukup `bash scripts/<helper>.sh`, bukan re-discover urutan SQL/docker/restart dari awal.

### Mengapa

- Setiap re-discovery boros context window (cari file, baca log, coba SQL, restart, verifikasi).
- Setiap re-discovery flaky — AI bisa skip step (misal lupa `TRUNCATE ytd_ledger` karena tidak FK ke periods, atau lupa rebuild image karena `docker restart` cuma re-run entrypoint).
- Setiap re-discovery menambah noise di chat dan menggeser fokus user dari kerjaan substantif.

### Trigger — kapan harus bikin script + runbook

Bikin helper begitu salah satu terjadi:

1. **AI sudah pernah debug urutan ini** — kalau next session bakal debug lagi dari nol, freeze sekarang.
2. **User bilang "kok ulang lagi sih"** atau sejenis — sinyal eksplisit bahwa flow ini perlu encapsulation.
3. **Ada > 3 step shell/docker/SQL berurutan dengan dependency** (misal: TRUNCATE → DELETE flyway row → restart container → wait health → verify seed).
4. **Step urutan punya racy timing** (misal Spring Boot accept TCP sebelum dispatcher servlet ready) — script harus encode probe, jangan andalkan AI ingat tambah `sleep`.

### Pola standar (3 file)

| File | Isi | Lokasi |
|---|---|---|
| Helper script | Eksekusi end-to-end. Idempotent. Exit non-zero on failure. Comment header explain WHY tiap step. | `scripts/<scope>-<verb>.sh` |
| Runbook MD | TL;DR (1 command), what it does, flags, when to update, known flakes, related links. | `docs/ops/{runbooks,testing}/<scope>-runbook.md` |
| CLAUDE.md ref | 1 line di On-Demand References pointing to runbook. | `CLAUDE.md` § On-Demand References |

### Contoh canonical (pattern, bukan file nyata)

- **`scripts/{domain}-reset.sh`** — reset domain DB ke baseline terdefinisi (TRUNCATE + restart + migration probe + HTTP probe + verify seed).
- **`scripts/test-{domain}-{flow}-{variant}.sh`** — wrapper: reset script + `npx playwright test {domain}-{flow}-{variant}`.
- **`docs/ops/testing/{domain}-{flow}-{variant}-runbook.md`** — runbook dirujuk dari `CLAUDE.md`.

Sebelum bikin script versi sendiri di sesi baru, **cek `scripts/` dulu** — kemungkinan helper-nya sudah ada.

### Anti-patterns

- ❌ Inline SQL panjang di chat untuk reset DB → bikin script.
- ❌ "Restart container, tunggu 30 detik, baru jalankan test" → script dengan health probe.
- ❌ Helper exists tapi tidak ada runbook + CLAUDE.md ref → AI sesi baru tidak akan tahu helper-nya ada → tetap re-discover.
- ❌ Runbook tanpa TL;DR satu-baris-command — runbook yang butuh dibaca 2 menit kalah cepat dengan re-discovery.

