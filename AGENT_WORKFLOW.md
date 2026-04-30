# Agent Workflow

Panduan agent pipeline: urutan eksekusi, input/output tiap agent, dan siapa yang mengkonsumsi hasilnya. Template reusable — project-level infra (scripts, runbooks, Makefile targets, drift detector binary) disetup terpisah per project.

---

## 5-Link Traceability Spine (v2)

> **Optional but strongly recommended for any project past initial PRD/FR drafting.** The 5-link spine ties PRD → FR → code → test scenario → test result so a single drift detector can flag any inconsistency between the layers. It is implemented today via 5 contract surfaces (4 markdown YAML blocks + 1 JSON state file) and a Go-based drift detector binary.
>
> **Canonical detector**: https://github.com/ahmadasror/drift-detector — public Go binary, MIT, ships all 5 schemas + working extractors. Adopt via `go install github.com/ahmadasror/drift-detector/cmd/drift-detector@latest` or fork for custom extractors.

```
PRD                FR             Code-comment       Test scenario      Test result
docs/prd/         docs/fr/       handler/service    docs/test-          docs/test-
<module>/         <module>/      docstring          scenarios/          reports/_ratchet/
*.md              *.md           // FR-X AC-Y       <module>/*.md       <scope>-state.json
  │ L1              │ L2              │ L3                │ L4                 │ L5
  └── PRD→FR ──────►│                 │                   │                    │
                    └── FR→code ─────►│                   │                    │
                                      └── code→FR comment►│                    │
                                                          └── FR→scenario ────►│
                                                          ◄── scenario→result ─┘
                                                              (ratchet history)
```

| Link | Direction | Source-of-truth | Schema | Owning agent | Drift `kind` |
|---|---|---|---|---|---|
| L1 | PRD → FR | `docs/prd/<module>/**/*.md` `## NN. PRD Contract Block` | `docs/prd/_contract-schema.json` | fr-writer | `prd_link` |
| L2 | FR → code/DB/wf | `docs/fr/<module>/*.md` `## NN. Contract` | `docs/fr/_contract-schema.json` | fr-writer + night-builder | `endpoint`, `permission`, `db_*`, `workflow_step` |
| L3 | code → FR (comment) | `*.go` / `*.java` leading doc-comment | regex grammar (no JSON Schema) | night-builder + fr-writer | `code_comment` |
| L4 | FR → test scenario | `docs/test-scenarios/<module>/{flow,api,fe}/*.md` `## NN. Test Contract Block` | `docs/test-scenarios/_contract-schema.json` | tester-explorer | `test_coverage`, `tc_orphan` |
| L5 | scenario → result | per-tier `docs/test-reports/_ratchet/<scope>-state.json` | `docs/test-reports/_ratchet-schema.json` + `_results-schema.json` | test-builder + CI | `test_ratchet` |

**Operational consequence for agents**: every agent in the pipeline now writes one or more contract surfaces (PRD block, FR block, leading doc-comment, scenario block, ratchet state). The drift detector reads all five and reports inconsistencies. Each agent's section below documents which surface(s) it owns.

**Adoption path**: see `PROPOSAL_FOR_OTHER_PROJECTS.md` for the recommended order — start with L2 (FR contract block) since it's the most actionable, then add L3 (code-comment marker), L4 (test scenario block), L5 (ratchet), L1 (PRD block) last.

---

## Pipeline Utama: Discovery → Build → Test → Supervise

```
requirement-gatherer
        │
        ├─ docs/prd/{module}/                        ← + PRD Contract Block (L1)
        └─ docs/architecture/domains/
                │
                ▼
        architect [Mode 1: solution-design]  ← wajib sekali per modul, pre-FR
                │
                ├─ docs/architecture/{module}/design.md   ← strategic: bounded context,
                │                                            entity model, patterns, NFR, ADRs
                └─ docs/architecture/adr/
                        │
                        ▼
                   fr-writer
                        │
                        └─ docs/fr/{module}/         ← + FR Contract Block (L2) + UI Selectors
                                │
                                ▼
                        architect [Mode 2: technical-spec]  ← post-FR, setelah FR tickets selesai
                                │
                                └─ docs/architecture/{module}/api-spec.md  ← API contracts,
                                         │                                    request/response,
                                         │                                    error codes,
                                         │                                    idempotency map
                                 ▼
                          tester-explorer  ← runs FIRST (P1+P2+P3 sequentially)
                                 │
                          docs/test-scenarios/{module}/   ← + Test Contract Block (L4)
                                 │
                                 ▼
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
            night-builder                 test-builder
            (source code +                (Playwright generate
             unit tests +                  + run + report
             code-comment markers L3)     + tier tags + TC IDs)
                  │                             │
                  ▼                             │
         architect [Mode 3: conformity]    docs/test-reports/
         (berkala, per sprint/milestone)        │
                  │                              ▼
         drift? ──YES──→ fr-writer         normalize-pw-results.sh
                  │            │                 │
                  NO    tester-explorer          ▼
                                 │       _ratchet/<scope>-state.json (L5)
                                 │                │
                                 └──────────────┐ │
                                                 ▼ ▼
                                           pimpro ← supervisi pipeline
                                           (baca: FR status + drift report
                                            + ratchet state + agent-log)
                                                 │
                                                 ▼
                                          drift-triager
                                          (per-kind classify, per-link sub-class)
```

**Aturan urutan:**

1. `requirement-gatherer` harus selesai dulu — PRD adalah input architect.
2. `architect` Mode 1 wajib dijalankan sebelum `fr-writer` — menghasilkan solution design: bounded context, entity model, integration pattern, NFR, ADR. **Belum sampai API endpoint detail** — itu wilayah Mode 2.
3. `architect` Mode 2 dijalankan setelah `fr-writer` selesai — derivasi API contracts dari FR tickets. Output `api-spec.md` adalah kontrak teknis untuk night-builder.
4. **`tester-explorer` berjalan FIRST setelah Mode 2 selesai** — produces 3-layer test scenarios (business + api + fe) sebagai validation contract.
5. **`night-builder` dan `test-builder` berjalan paralel SETELAH tester-explorer SELESAI (P1+P2+P3 done)** — keduanya consume test scenarios sebagai input wajib. (Update from earlier pipeline order — sebelumnya tester-explorer ‖ night-builder paralel; sekarang sequential supaya night-builder dapat scenarios sebagai validation contract sebelum implementasi.)
6. Setelah implementasi berjalan, `architect` Mode 3 (conformity checkpoint) — membandingkan kode dengan `design.md` + `api-spec.md`, melaporkan drift, membuat ADR baru bila ada keputusan yang belum terdokumentasi.
7. Jika conformity checkpoint menemukan drift signifikan → **loop ke fr-writer** untuk update FR yang terpengaruh, lalu tester-explorer untuk update test scenarios.
8. `night-builder` membaca FR + `api-spec.md` + **`docs/test-scenarios/{module}/` (wajib)** + codebase — test scenarios adalah validation contract, bukan opsional.
9. `drift-triager` runs after every drift detector run — classifies entries, recommends fix path. Read-only; never edits FR/code.
10. `pimpro` runs on every agent completion (event-driven via hook) — updates only the Recent Activity section. Full sweep only on user trigger.

**Error traceability:**
- Playwright inject `X-Request-ID: pw-{id}` di setiap request
- Kalau test gagal: `docker logs {service-name} 2>&1 | grep "<RUN_ID>"`
- Log management: stdout Docker umumnya cukup untuk project kecil/menengah. Opsi self-host ringan: **Seq** (1 container, ~200MB) — search log via UI, filter by request ID

---

## Cross-Agent Contract — UI Selectors

> Contract ini muncul dari insiden di mana test assertion memakai `data-testid` yang tidak sama dengan yang diimplementasikan di template — test pass, padahal elemen tidak pernah match. Sejak itu, testid ditetapkan di FR dulu sebelum implementasi dan test code lahir.
> **Spec lengkap** (per project): `docs/architecture/testing/ui-selector-contract.md`.

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

### Naming (ringkas)

| Prefix | Contoh | Peran |
|---|---|---|
| `{domain}-{action}-btn` | `submit-review-btn` | Button action |
| `{action}-{entity}-dialog` | `confirm-transition-dialog` | Modal/dialog root (portaled) |
| `{entity}-{field}-input` | `{entity}-{field}-input` | Input field |
| `{entity}-{field}-select` | `{entity}-{field}-select` | Dropdown |
| `{domain}-{role}` | `summary-{metric}` | StatCard value |
| `{entity}-table` | `{entity}-results-table` | DataTable |

### Anti-patterns (auto-reject di review)

- Invent testid di spec: `page.getByTestId('probably-this-one')`
- Rename testid untuk "lebih bagus" — renames break every consumer
- Embed UUID atau state di testid: `submit-btn-disabled` (state properti, bukan identity)
- Chain `getByTestId(dialog).getByRole(button)` untuk portaled dialog — gunakan helper project (misal `e2e/helpers/portal-dialog.ts`) yang unwrap portal dulu.

---

## Cross-Agent Contract — FR Contract Block (drift detector L2)

Setiap FR di-modul in-scope wajib punya `## Contract (machine-readable)` section dengan YAML twin block sesuai `docs/fr/_contract-schema.json`. Kontrak ini mengikat:

| Stage | Agent | Tanggung jawab |
|---|---|---|
| **Generate** | `fr-writer` (Step 7) | Tulis YAML block sebagai bagian Step 7. Source dari `## API Response Codes` table, `## Actors & RBAC`, `## Data Model Touch Points` yang sudah ditulis Step 1–6. Sertakan `prd_refs[]` opsional bila PRD sudah punya `anchors[]`. |
| **Backfill** | `scripts/build-fr-contract-blocks.py` | One-shot generator parse markdown table existing → seed YAML skeleton dengan TODO marker |
| **Validate** | `make drift-validate` (CI gate) | Schema validation per `_contract-schema.json` — Phase 1 hard gate |
| **Detect** | `<project>-drift check` (CI artifact) | Compare claim vs Go/Java route + Postgres + workflow YAML reality — Phase 1 warning, Phase 2 blocking |
| **Triage** | `drift-triager` agent | Classify FR-ahead / Code-ahead / Real-mismatch / Waiver-eligible × P0/P1/P2 — recommend agent untuk fix |
| **Aggregate** | `pimpro` | Render Drift Status section di `docs/pimpro/status.md` dengan severity counts |

In-scope modules: per project — typically modules whose FR layer has matured. Out-of-scope (Phase 2): pre-FR or actively-evolving modules.

### `prd_refs[]` (additive, v2 Phase 4)

Setiap FR contract block boleh declare `prd_refs[]` yang back-link ke PRD anchor. Field opsional (FR tanpa `prd_refs[]` tetap valid). Drift detector emits `fr_orphan_prd_ref` (P2) bila PRD file atau anchor yang dirujuk tidak ada.

```yaml
prd_refs:
  - prd_file: docs/prd/<module>/index.md
    anchor: <anchor-slug>           # must exist in PRD's `anchors[]`
  - prd_file: docs/prd/<module>/index.md
    anchor: full-prd                # reserved slug for whole-PRD reference
```

Rule reference: `rules/fr-contract-block.md`.

---

## Cross-Agent Contract — Code-Comment FR-Marker (drift detector L3)

> Sister kontrak ke FR contract block — both must hold for v2 spine compliance.

### Konvensi

Setiap **public method** di tipe `*Handler|*Service|*Repository|*Controller` (Java) atau exported func di `internal/{handler,service,repository,middleware}/` (Go) untuk modul in-scope WAJIB punya leading doc-comment yang berisi salah satu dari:

| Marker | Semantik |
|---|---|
| `FR-<MODULE>-<NNN> [AC-<N>]` | Real reference. Prefix `[A-Z]{2,15}` (e.g. `FR-008`, `FR-MOD-008`). AC suffix flat (`AC-3`) atau compound (`AC-001-3`). |
| `audit:skip — <reason>` | Intentional non-emit di CUD path. Reason mandatory. |
| `fr:internal` | Method tidak punya user-facing surface (cache helper, internal RPC). |
| `fr:exempt — <reason>` | Intentional gap dengan reference (ADR id, ticket, follow-up FR). |
| `FR-TBD` | Time-boxed placeholder. TTL 90-hari via ledger `docs/drift-reports/_marker-state.json`. |

Precedence (first match wins): `FR > TBD > SKIP > EXEMPT > INTERNAL`.

### Placement (D2 — leading-only)

- **Java**: di dalam `/** ... */` Javadoc yang precede method (allow `@Annotation` lines antara Javadoc close + method signature).
- **Go**: di `//` lines tepat di atas `func`, no blank line.

Mid-method comments dan trailing comments **tidak** count. Scanner pakai `*ast.FuncDecl.Doc` (Go) + 60-line lookback window (Java) — Javadoc bodies > 60 lines flagged `javadoc_too_long` (P2).

### Tanggung jawab per agent

| Agent | Kewajiban terkait L3 |
|---|---|
| **fr-writer** | Saat author FR baru, listing AC harus cukup spesifik supaya night-builder bisa map method ke `FR-X AC-N`. Saat triage `marker_orphan_fr` dari drift report, fr-writer fix atau hapus FR yang tidak ada (typo). |
| **night-builder** | Setiap method baru yang ditulis WAJIB ada leading marker. Saat backfill module baru, ikuti bucket convention (B1 FR-AC mapped, B2 fr:internal, B3 fr:exempt-known, B4 FR-gap, B5 FR-TBD) — triage FIRST (~30 min), edit SECOND (mechanical). |
| **drift-triager** | Per-kind sub-class di `kind: code_comment`: `marker_missing` → night-builder atau fr-writer (tergantung bucket); `marker_orphan_fr` → fr-writer; `marker_tbd` → P2 informational sampai 30d, P1 sampai 90d, P1 escalating after; `javadoc_too_long` → manual_review (refactor Javadoc). |

### Enforcement

1. **Extractor**: `code_comment` di `<project>-drift check`. Opt-out: `--skip-extractor code_comment`.
2. **Strict mode**: `make drift-strict` runs `--strict-modules <list>` — drift di modul itu return non-zero (P0/blocking). Modul in-scope lain warning-only sampai CI promotion.
3. **Auto-stub**: `bash scripts/fr-tbd-stub.sh --module <m>` seed `FR-TBD` placeholders idempotent — doc-comment edits saja, tidak pernah touch executable code.
4. **TTL ledger**: `docs/drift-reports/_marker-state.json` records first-seen date per `FR-TBD`. Differ escalates to `marker_missing` (P1) at day 90.

---

## Cross-Agent Contract — Test Scenario Contract Block (drift detector L4)

> Sister kontrak FR contract block + code-comment marker.

### Konvensi

Setiap file di `docs/test-scenarios/<module>/{flow,api,fe}/*.md` WAJIB punya last section:

```markdown
## NN. Test Contract Block (machine-readable)

> Drift-detector source. Schema: `docs/test-scenarios/_contract-schema.json`.

```yaml
ts_file: docs/test-scenarios/<module>/api/flow-NN-<name>.md
layer: api                                    # business | api | fe
covers: [TC-MOD-001-HP-001, ...]              # mirror of tcs[].id
tcs:
  - id: TC-MOD-001-HP-001
    title: HR submits valid form
    traces_to: [FR-MOD-001 AC-1]              # flat or compound (FR-MOD-001 AC-001-1)
    type: HP                                  # HP|SP|BR|AUDIT|EDGE|CONC|IDEM|VAL|PRE|POST|BS|FE
    seed: V14                                  # optional — Flyway / migration version
    fixme: true                                # optional — TC blocked on backend wire-up
cross_links:
  fr_files: [docs/fr/<module>/fr-<feature>.md]
  sister_scenarios:
    - docs/test-scenarios/<module>/flow-NN-<name>.md
    - docs/test-scenarios/<module>/fe/flow-NN-<name>.md
```
```

### TC ID format

Module-flexible (regex enforced by extractor, not schema):
- API layer: `TC-<MODULE>-<NNN>-<TYPE>-<NNN>` (e.g. `TC-MOD-001-HP-001`)
- Compound: `TC-<MODULE>-L<NN>-<LETTER>-<NNN>` (e.g. `TC-MOD-L01-A-001`)
- Business-layer aggregate: `BS-<NN>-<NN>` (e.g. `BS-01-01`)
- FE layer: `FE-<NN>-<NN>` (e.g. `FE-01-34`)
- Smoke: `TC-SMK-<TYPE>-<NNN>`

`traces_to[]` regex: `^FR-[A-Z0-9-]+\s+AC-[A-Z0-9-]+$` — uppercase, flat or compound suffix.

### Tanggung jawab per agent

| Agent | Kewajiban terkait L4 |
|---|---|
| **tester-explorer** | Author block sebagai output Phase 3. Setiap TC harus map ke ≥1 FR-AC pair di `traces_to[]`. Kalau gap, write `traces_to: []` (explicit drift signal) — jangan invent mapping palsu. |
| **test-builder** | Tag Playwright test name dengan TC ID supaya L5 ratchet bisa join (`TC-XXX-NNN` substring di test title). Bukan author scenario block — itu tester-explorer responsibility. |
| **drift-triager** | Per-kind di `kind: test_coverage`: `ac_uncovered` → tester-explorer (write TC) atau accept (intentional, FR set `test_coverage.required: false`); `ts_block_invalid` → manual_review (schema fix). Per-kind di `kind: tc_orphan`: `traces_to_empty` → tester-explorer pair-curate; `traces_to_unknown_fr/ac` → fr-writer (FR missing) atau manual_review (typo). |

---

## Cross-Agent Contract — Test Result Ratchet (drift detector L5)

> Closes the spine — green→red regression detection across runs.

### Per-tier scopes

Setiap tier punya state file sendiri supaya scope shrinkage (T1 ⊂ T2) tidak menghasilkan false-positive `silent_drop`:

| Tier | Scope key | State file | Driver Makefile target |
|---|---|---|---|
| T0 smoke (cross-module) | `smoke` | `docs/test-reports/_ratchet/smoke-state.json` | `make test-t0` |
| T1 critical (per module) | `<module>-t1` | `docs/test-reports/_ratchet/<module>-t1-state.json` | `make test-<module>-critical` |
| T2 full (per module) | `<module>-t2` | `docs/test-reports/_ratchet/<module>-t2-state.json` | `make test-<module>-full` |

Future tiers extend the same convention.

### Pipeline

```bash
make test-t0
  ├─ npx playwright test --grep @t0
  ├─ bash scripts/normalize-pw-results.sh --scope smoke
  │   └─ writes docs/test-reports/<run-id>-smoke-results.json
  └─ <project>-drift check --ratchet-scope smoke --ratchet-update
      └─ updates docs/test-reports/_ratchet/smoke-state.json (rolling N=10)
```

Ratchet state shape (per scope):

```json
{
  "schema_version": 1,
  "scope": "<module>-t1",
  "buffer_max": 10,
  "tcs": [
    {
      "tc_id": "TC-MOD-001-HP-001",
      "last_status": "passed",
      "green_streak": 5,
      "states": [{"run_id": "...", "status": "passed", "ts": "..."}, ...]
    }
  ]
}
```

### Drift kinds

| Kind | Severity | Trigger |
|---|---|---|
| `regression` | **P0** | `passed → failed` or `passed → timed_out` |
| `silent_drop` | P1 | `passed → missing` (state had it, latest run doesn't) — check tier-mismatch first |
| `green_streak_broken` | P1 (additive) | TC was green for ≥5 consecutive runs and flipped — high-confidence accumulator with `regression` |
| `tc_unknown` | P2 | Test title carries TC pattern but no L4 scenario block declares it — recommend tester-explorer |

### CI red line — PR jobs never mutate ratchet state

| Stage | Mode |
|---|---|
| **PR gate** (`drift-check.yml`) | **Read-only** — never `--ratchet-update`. PR runs allowed to update state would whitewash regressions sami-sami. |
| **Nightly** (`drift-nightly.yml`) | Mutates state via `--ratchet-update` after canonical run. Default `include_t2: false` (opt-in untuk longer wall-time). |

### Tanggung jawab per agent

| Agent | Kewajiban terkait L5 |
|---|---|
| **test-builder** | Generate test names dengan TC ID substring (e.g. `test('TC-MOD-001-HP-001 — submit form', ...)`) supaya normalizer bisa map title → tc_id. |
| **drift-triager** | Per-kind di `kind: test_ratchet`: `regression` → engineer triage (test owner via FR-AC); `silent_drop` → check tier-mismatch FIRST sebelum flag; `green_streak_broken` → additive context; `tc_unknown` → tester-explorer. |
| **pimpro** | Read-only L5 row per scope (latest run, regression count, green streak average). Tidak boleh trigger `--ratchet-update`. |

---

## Cross-Agent Contract — PRD Contract Block (drift detector L1)

> Closes the back-end of the spine — PRD declares which FRs implement it; FR optionally back-links to PRD anchor.

### Konvensi

Setiap PRD di modul mature WAJIB punya `## NN. PRD Contract Block (machine-readable)` sebagai last section:

```markdown
## NN. PRD Contract Block (machine-readable)

> Drift-detector source. Schema: `docs/prd/_contract-schema.json`.

```yaml
prd_file: docs/prd/<module>/index.md
status: approved              # draft | approved | superseded
last_review_date: 2026-04-30
owner: <product team>
covers:                       # FR IDs that implement this PRD
  - FR-MOD-001
  - FR-MOD-002
anchors:                      # optional — for fine-grained FR `prd_refs[].anchor` targeting
  - id: <anchor-slug>
    title: "§3 <Section title>"
cross_links:
  fr_files: [docs/fr/<module>/fr-<feature>.md, ...]
  superseded_by: docs/prd/<module>/v2.md   # required when status=superseded
  sister_prds: [...]
```
```

### Tanggung jawab per agent

| Agent | Kewajiban terkait L1 |
|---|---|
| **requirement-gatherer** | Saat author PRD baru di modul mature, generate skeleton block. Listing `covers[]` dari Flow Map → FR mapping. |
| **fr-writer** | Saat author FR di modul yang sudah punya PRD block, opsional declare `prd_refs[]` di FR contract block (additive). Anchor harus exist di PRD `anchors[]`. |
| **drift-triager** | Per-kind di `kind: prd_link`: `prd_orphan_fr` → fr-writer (FR missing) atau manual_review (typo); `fr_orphan_prd_ref` → fr-writer (typo) atau manual_review (PRD deleted); `prd_no_block` → P3 informational (gradient adoption); `prd_block_invalid` → manual_review (schema fix). |

---

## Cross-Agent Contract — Test Tiering

> Tiering memisahkan tests berdasarkan business frequency × blast radius supaya PR feedback < 5 menit, pre-merge < 20 menit, full coverage tetap berjalan nightly.

### Tier definitions

| Tier | Cakupan | Wall clock target | Frekuensi run | Tag |
|---|---|---|---|---|
| **T0 smoke** | login + 1 happy path | ~2 m | every PR | `@t0` |
| **T1 critical regression** | happy path semua flow + monthly events | ~15 m | every push to main | `@t1` |
| **T2 full regression** | T1 + edge cases + SP/AUTH/IDEM/BR | ~30 m | nightly | `@t2` |
| **T3 long-running** | visual diff, PDF render, perf, chaos | terpisah | weekly | `@t3` |

T0 ⊂ T1 ⊂ T2. T3 disjoint. Tag bersifat additive — sebuah test bisa punya `@t1 @t2 @critical @monthly` sekaligus.

### Tanggung jawab per agent

| Agent | Kewajiban terkait Tiering |
|---|---|
| **tester-explorer** | Setiap business scenario doc wajib punya field `## Tier:` + `## Reason:` per TC. Default: rule-of-thumb `frequency × blast radius`. Bulanan + happy path + blocker = T1; tahunan atau edge case = T2; visual atau chaos = T3. Eksplisit boleh override (FR atau user mention) — saat tidak eksplisit, rule-of-thumb cukup. |
| **test-builder** | Mechanical: baca tier dari scenario doc → apply Playwright tag `{ tag: ['@t1', '@critical', '@monthly'] }` di setiap test. Tidak ada judgment di sini — tag persis seperti yang ditulis tester-explorer. Kalau scenario doc absent tier field → flag back ke tester-explorer, jangan tebak. |
| **Manual gate** (project owner) | Promotion `@wip` → `@t1`/`@t2` adalah keputusan manusia. Gate: 3 nightly run berturut-turut hijau, no flake, explicit PR sign-off. tester-explorer dan test-builder tidak punya wewenang promote. |

### Enforcement layers

1. **Scenario doc review** — `## Tier:` field wajib ada di setiap TC sebelum test-builder diizinkan generate. `tier:` hilang = block.
2. **Tag application** — test-builder generate tag persis dari scenario doc. CI lint memastikan setiap test punya minimal 1 tier tag.
3. **CI matrix** — fixed schedule, tidak boleh diubah ad-hoc:
   - Every PR → `--grep @t0`
   - Every push to `main` → `--grep @t1`
   - Nightly cron → `--grep @t2`
   - Weekly cron (release branch) → `--grep @t3`
4. **Per-tier reports** — `gen-report.js` produce file terpisah per tier (`smoke-report.md`, `regression-report.md`, `weekly-report.md`).

### Tag taxonomy (canonical)

| Category | Tags | Meaning |
|---|---|---|
| Tier (≥1 wajib) | `@t0` `@t1` `@t2` `@t3` `@wip` | tier mana test ini run |
| Frequency hint | `@monthly` `@annual` `@event-driven` `@release` | business frequency real |
| Stability | `@stable` `@flaky` `@wip` | promotion gate |
| Specialization | `@visual` `@perf` `@chaos` `@audit` | reason masuk T3 |

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
| PRD index | `docs/prd/{module}/index.md` (+ PRD Contract Block when module is mature) | Per modul |
| PRD per-workflow | `docs/prd/{module}/{workflow}.md` | Per workflow |

### Struktur PRD index
- Executive summary
- Personas
- Domains Affected (table: domain / read-write / operations)
- **Flow Map** — satu block per end-to-end business process (Trigger, Actor, Outcome, Prerequisite, Business steps, PRD workflows)
- **Workflow File Map** — tabel mapping file workflow ke FRs dan domain
- NFR summary
- References (link ke discovery, domain map, FR layer)
- **PRD Contract Block** (last section) — when module mature

> Flow Map adalah kontrak antara PRD dan FR layer. fr-writer membacanya dan menambahkan FR refs, ticket refs, dan test scenario links ke tiap flow block.

### Flow Map vs PRD Workflows — perbedaan

| | Flow Map (F-NN) | PRD Workflows |
|---|---|---|
| **Perspektif** | User journey — satu user goal selesai | Functional capability — apa yang sistem bisa lakukan |
| **Unit** | End-to-end business process | Satu domain/kapabilitas fungsional |
| **Isi** | Trigger, Actor, Outcome, Prerequisite, Business steps | Business rules detail, state machine, data model, validation |
| **Granularitas** | Coarse — "apa yang user capai" | Fine — "bagaimana sistem melakukannya" |

**Flow Map** menjawab *"user mau apa?"*  
**PRD Workflows** menjawab *"sistem ngapain?"*

### Dikonsumsi oleh
- **fr-writer** — membaca PRD sebagai input utama
- **architect** — membaca domain map untuk system design
- **tester-explorer** — membaca PRD sebagai Layer 1

### Handoff
Selesai di PRD. Tidak menyentuh kode. Bilang ke user untuk jalankan `fr-writer` selanjutnya.

---

## Agent 2 — architect *(Solution Architect)*

**Model**: Opus | **Kapan**: Tiga mode berbeda sepanjang pipeline — pre-FR, post-FR, dan post-implementasi.

### Tiga Mode

| Mode | Trigger | Output | Dikonsumsi |
|---|---|---|---|
| **1 — solution-design** | requirement-gatherer selesai, sebelum fr-writer | `design.md` | fr-writer |
| **2 — technical-spec** | fr-writer selesai, sebelum night-builder | `api-spec.md` | night-builder, tester-explorer |
| **3 — conformity** | Setelah implementasi berjalan — per sprint/milestone | Conversation only | fr-writer (bila drift) · pimpro |

### Mode 1 — solution-design (pre-FR)

**Scope:** Keputusan strategis saja — belum sampai API endpoint detail.
- Bounded context dan service responsibilities
- Data model level entity (bukan DDL, bukan field list lengkap)
- Integration patterns (sync/async, event-driven, saga)
- Resilience decisions, NFR constraints
- Technology decisions yang perlu ADR

**Output:** `docs/architecture/{module}/design.md` · ADRs strategis di `docs/architecture/adr/`.

### Mode 2 — technical-spec (post-FR)

**Scope:** Derivasi technical spec dari FR yang sudah terdefinisi.
- API contracts: endpoint, method, request/response shape, error codes
- State transition codes konsisten dengan AC di FR
- Idempotency map
- Field-level constraints (tipe data, presisi)
- ADR baru bila ada keputusan teknis yang muncul dari FR detail

**Output:** `docs/architecture/{module}/api-spec.md` · ADRs taktis.

### Mode 3 — conformity (post-implementasi)

**Scope:** Tidak menghasilkan doc baru — membandingkan kode dengan kedua baseline, melaporkan drift.
- Apa yang sudah sesuai
- Apa yang menyimpang (dan seberapa signifikan)
- ADR baru bila ada keputusan implementasi yang belum terdokumentasi

**Output:** Conversation only. Bila drift signifikan → trigger fr-writer update.

---

## Agent 3 — fr-writer

**Model**: Opus | **Kapan**: Setelah PRD (dan optionally architecture) tersedia

### Output

| Artifact | Path | Isi |
|---|---|---|
| FR index | `docs/fr/{module}/index.md` | Epic breakdown, flow map, ticket index |
| FR per-workflow | `docs/fr/{module}/fr-{workflow}.md` | Epics, ticket stubs, AC tables, response codes, **`## UI Selectors` section** (wajib bila FR punya UI surface), **FR Contract Block** (last section, drift detector L2) |
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
- Architecture: `docs/architecture/{module}/api-spec.md` (Layer 3 — expected values, error codes, idempotency map)

### Output

Single progressive file, 3 phases. **Phase 3 output now includes Test Scenario Contract Block (L4) per scenario file.**

| Phase | Isi | Path |
|---|---|---|
| Phase 1 | Workflow, state machine, BR inventory, AC log | `docs/test-scenarios/{module}/tester-{domain}-{date}.md` |
| Phase 2 | Seed data map, precondition templates | Append ke file Phase 1 |
| Phase 3 | Test scenarios + Test Contract Block per file | `docs/test-scenarios/{module}/{flow,api,fe}/*.md` (each with `## NN. Test Contract Block`) |

### Kategori test scenario
`HP` Happy Path · `SP` Sad Path · `ST` State Transition Valid · `STX` State Transition Invalid · `BR` Business Rule · `AUTH` Authorization · `IDEM` Idempotency · `CONC` Concurrency · `EDGE` Boundary · `INT` Integration · `AUDIT` Audit Trail · `COMP` Rollback/Compensation

### Tier annotation per TC (wajib)

Setiap test case di scenario doc **wajib** punya field tier — lihat Test Tiering contract. Format minimal:

```markdown
### TC-MOD-001-HP-001: HR submits valid form

**Tier**: T1 critical
**Reason**: Bulanan, happy path, blocker kalau gagal
**Tags**: `@t1 @critical @monthly`

**Given**: ...
**When**: ...
**Then**: ...
```

### Dikonsumsi oleh
- **QA** — manual testing dari Phase 3 scenarios
- **night-builder** — automated test implementation
- **test-builder** — tier annotation → Playwright tags (mechanical apply)
- **Engineers** — referensi edge cases saat build

---

## Agent 5 — test-builder

**Model**: Sonnet | **Kapan**: Setelah tester-explorer Phase 3 selesai

### Input
- Test scenarios: `docs/test-scenarios/{module}/api/flow-NN-*.md` + `docs/test-scenarios/{module}/fe/flow-NN-*.md`
- `CLAUDE.md` untuk credentials, API envelope, service URLs
- Existing `e2e/tests/{module}/` untuk pattern reference

### Output
- `e2e/tests/{module}/{module}-flow{NN}-api.spec.ts` — Playwright APIRequestContext (API layer)
- `e2e/tests/{module}/{module}-flow{NN}-{name}.spec.ts` — Playwright browser E2E (FE layer)
- Test names embed TC ID substring → L5 ratchet can join JSON results
- Each test carries `tag: ['@tN', ...]` matching scenario doc Tier field
- Run + report: see test-builder agent doc

### Batasan
- **Tidak menyentuh source code** — hanya baca test scenarios, tulis test files
- **Tidak generate backend unit tests** — backend unit/controller test tanggung jawab night-builder
- **`data-testid` dari FR, bukan tebak**
- **Tier tag dari scenario doc, bukan tebak**
- **TC ID substring di test title wajib** — supaya L5 ratchet bisa match Playwright JSON → scenario block
- `test.fixme()` untuk TC yang butuh seed state di luar default seed
- `X-Request-ID: pw-{id}` di-inject ke semua requests untuk error traceability

---

## Agent 6 — night-builder

**Model**: Sonnet | **Kapan**: Autonomous overnight implementation

### Input
- FR: `docs/fr/{module}/`
- Architecture: `docs/architecture/{module}/design.md` · `docs/architecture/{module}/api-spec.md`
- Test scenarios: `docs/test-scenarios/{module}/` (mandatory — validation contract)
- Codebase (read + write)

### Output
- Code implementation (source code + backend unit/controller tests)
- **Code-comment FR markers (L3)** — every public method on `*Handler|*Service|*Repository|*Controller` has leading doc-comment with marker (`FR-X AC-Y` / `audit:skip` / `fr:internal` / `fr:exempt` / `FR-TBD`)
- Report: `docs/night-builds/{date}-{topic}-report.md`

---

## Agent 7 — pimpro *(supervisor)*

**Model**: Sonnet | **Kapan**: Default mode A (event-driven on every agent completion via SubagentStop hook). Mode B (full sweep) only on user trigger.

### Mode A — event-driven (default)
- Reads `docs/pimpro/agent-log.jsonl` (last 50 entries)
- Updates only `## Recent Agent Activity (last 20)` section in `docs/pimpro/status.md`
- Idempotent — no churn if no new entries

### Mode B — full sweep (user-triggered)
- Reads canonical status, all artifacts, drift report, ratchet state
- Refreshes Pipeline Dashboard, Drift Status (per link L1..L5), Recommended Next Actions
- Writes to `docs/pimpro/status.md` (canonical) or `docs/pimpro/status-{date}.md` (dated archive policy)

### Inputs
- `docs/fr/status.md` — canonical status tracker
- Existence check per artifact per modul
- Status header (first 20 lines) of each agent-owned doc
- Night-builder reports: `docs/night-builds/`
- Test reports: `docs/test-reports/`
- Drift report: `docs/drift-reports/<latest-date>/report-drift.json`
- Triage report: `docs/drift-reports/YYYY-MM-DD-triage.md`
- Ratchet state: `docs/test-reports/_ratchet/<scope>-state.json`
- Marker ledger: `docs/drift-reports/_marker-state.json`

### Boundaries
- Write only to `docs/pimpro/`
- Read-only against ratchet state — never mutate
- Do NOT run drift detector binary itself
- Do NOT classify drift entries — that's drift-triager
- Do NOT modify FR/PRD/scenario contract blocks

---

## Agent 8 — drift-triager *(post-drift triage)*

**Model**: Sonnet | **Kapan**: After every drift detector run

### Input
- Latest drift report: `docs/drift-reports/<latest-date>/report-drift.json`
- All contract schemas (FR, PRD, scenario, ratchet)
- FR/PRD/scenario claim blocks + code/DB samples + git history

### Output
- `docs/drift-reports/YYYY-MM-DD-triage.md` — classification + recommendations

### Classification matrix
- 4-class root cause: FR-ahead / Code-ahead / Real-mismatch / Waiver-eligible
- Per-kind sub-class: `code_comment` / `test_coverage` / `tc_orphan` / `test_ratchet` / `prd_link` (each with own `reason` discriminator)
- Severity P0/P1/P2 + confidence high/low

### Boundaries
- Read-only — never edits FR / code / migrations
- Never invokes other agents (Phase 1)
- Never auto-creates waivers
- Recommendations only — user dispatches

---

## Agent Contract Table

| Agent | Input | Produces | Dikonsumsi oleh |
|---|---|---|---|
| **requirement-gatherer** | User intent · `docs/` existing · `CLAUDE.md` | `docs/discovery/` · `docs/architecture/domains/` · `docs/prd/{module}/` (+ PRD Contract Block when mature) | architect · fr-writer · tester-explorer |
| **architect** *(Mode 1)* | `docs/prd/{module}/` · `docs/discovery/` · codebase | `docs/architecture/{module}/design.md` · ADRs strategis | fr-writer |
| **architect** *(Mode 2)* | `docs/fr/{module}/` · `docs/architecture/{module}/design.md` | `docs/architecture/{module}/api-spec.md` · ADRs taktis | night-builder · tester-explorer |
| **architect** *(Mode 3)* | `docs/architecture/{module}/design.md` · `api-spec.md` · `docs/fr/{module}/` · codebase | Conformity report (conversation) · ADR baru bila drift | fr-writer (bila drift) · pimpro |
| **fr-writer** | `docs/prd/{module}/` · `docs/architecture/{module}/design.md` | `docs/fr/{module}/index.md` · `docs/fr/{module}/fr-{workflow}.md` (incl. `## UI Selectors` + FR Contract Block) · `docs/fr/{module}/completion-status.md` | tester-explorer · engineers · night-builder · test-builder · pimpro |
| **tester-explorer** | `docs/prd/{module}/` · `docs/fr/{module}/` · `api-spec.md` · seed data | `docs/test-scenarios/{module}/` (3 phases + Test Contract Block per file) | QA · test-builder · night-builder · engineers · pimpro |
| **test-builder** | `docs/test-scenarios/{module}/api+fe/` · `CLAUDE.md` | `e2e/tests/{module}/*.spec.ts` (TC ID + tier tag mandatory) · `docs/test-reports/{date}-report.md` · ratchet input via normalizer | QA · engineers · pimpro · ratchet |
| **night-builder** | `docs/fr/{module}/` · `docs/architecture/{module}/design.md` · `docs/architecture/{module}/api-spec.md` · `docs/test-scenarios/{module}/` (mandatory) · codebase | Source code + backend unit tests + L3 code-comment markers · `docs/night-builds/{date}-report.md` | pimpro · drift-triager |
| **drift-triager** | `docs/drift-reports/<date>/report-drift.json` · contract schemas · FR/PRD/scenario files · git log | `docs/drift-reports/YYYY-MM-DD-triage.md` | fr-writer · night-builder · tester-explorer · pimpro |
| **pimpro** | `docs/fr/status.md` · artifact existence · status headers · night-build reports · test reports · drift report · triage · ratchet state · agent-log | `docs/pimpro/status.md` — pipeline dashboard + drift status + recent activity | User / project owner |

---

## Agent Pendukung (non-pipeline)

| Agent | Kapan dipakai | Output |
|---|---|---|
| `security-reviewer` | Security audit — sebelum release | Security findings |
| `planner` | Planning implementasi fitur spesifik | Implementation plan |
| `presenter` | Slide deck manajemen | HTML presentation |
| `architect-financial` | Review arsitektur financial-grade | Architecture review |

---

## Quick Reference: Jalankan Agent

```bash
# Discovery modul baru
# Invoke: requirement-gatherer
# Prompt: "Buat PRD untuk modul {module-name}"

# Architecture — Mode 1: solution-design (wajib sebelum fr-writer)
# Invoke: architect
# Prompt: "Solution design untuk modul {module-name} dari docs/prd/{module-name}/ — Mode 1, output design.md"

# Architecture — Mode 2: technical-spec (setelah fr-writer selesai)
# Invoke: architect
# Prompt: "Technical spec untuk modul {module-name} dari docs/fr/{module-name}/ — Mode 2, output api-spec.md"

# FR dari PRD yang sudah ada (incl. FR Contract Block per file)
# Invoke: fr-writer
# Prompt: "Buat FR untuk modul {module-name} dari docs/prd/{module-name}/"

# Test scenarios dari FR (incl. Test Contract Block per file)
# Invoke: tester-explorer
# Prompt: "Explore domain {module-name}"

# Generate Playwright test code dari test scenarios
# Invoke: test-builder
# Prompt: "Build {module} F-01..F-N, all flows"

# Autonomous build overnight (source code + unit tests + L3 markers)
# Invoke: night-builder
# Prompt: "Implement {FR-IDs} dari docs/fr/{module}/fr-{workflow}.md"

# Triage drift detector output
# Invoke: drift-triager
# Prompt: "Triage latest drift report"

# Project status dashboard (mode A — Recent Activity only)
# Invoke: pimpro
# (no prompt needed — picks up agent-log)

# Project status dashboard (mode B — full sweep)
# Invoke: pimpro
# Prompt: "Pimpro full scan" (or any trigger phrase: "scan everything", "refresh full")
```

### Supporting agents (non-pipeline)

```bash
# Financial-grade forensic audit review
# Invoke: architect-financial
# Prompt: "Audit {module} untuk idempotency + immutable ledger compliance"

# Security vulnerability review
# Invoke: security-reviewer
# Prompt: "Audit {service-path}/ untuk OWASP Top 10"

# Implementation planning
# Invoke: planner
# Prompt: "Plan implementation for {FR-ID} dari docs/fr/{module}/"

# HTML slide deck (management-level)
# Invoke: presenter
# Prompt: "Generate deck for {topic}, target audience: management"
```

---

## AI Discovery — Helper Scripts vs Re-Discovery

**Prinsip:** setiap operasi yang AI pernah debug & solve harus jadi **helper script di `scripts/`** + **runbook di `docs/ops/{runbooks,testing}/`** + **referensi di `CLAUDE.md`**. Tujuannya: sesi berikutnya AI cukup `bash scripts/<helper>.sh`, bukan re-discover urutan SQL/docker/restart dari awal.

### Mengapa

- Setiap re-discovery boros context window (cari file, baca log, coba SQL, restart, verifikasi).
- Setiap re-discovery flaky — AI bisa skip step (misal lupa TRUNCATE tabel turunan yang tidak punya FK, atau lupa rebuild image karena `docker restart` cuma re-run entrypoint).
- Setiap re-discovery menambah noise di chat dan menggeser fokus user dari kerjaan substantif.

### Trigger — kapan harus bikin script + runbook

Bikin helper begitu salah satu terjadi:

1. **AI sudah pernah debug urutan ini** — kalau next session bakal debug lagi dari nol, freeze sekarang.
2. **User bilang "kok ulang lagi sih"** atau sejenis — sinyal eksplisit bahwa flow ini perlu encapsulation.
3. **Ada > 3 step shell/docker/SQL berurutan dengan dependency** (misal: TRUNCATE → DELETE migration history row → restart container → wait health → verify seed).
4. **Step urutan punya racy timing** (misal container accept TCP sebelum app layer ready) — script harus encode probe, jangan andalkan AI ingat tambah `sleep`.

### Pola standar (3 file)

| File | Isi | Lokasi |
|---|---|---|
| Helper script | Eksekusi end-to-end. Idempotent. Exit non-zero on failure. Comment header explain WHY tiap step. | `scripts/<scope>-<verb>.sh` |
| Runbook MD | TL;DR (1 command), what it does, flags, when to update, known flakes, related links. | `docs/ops/{runbooks,testing}/<scope>-runbook.md` |
| CLAUDE.md ref | 1 line di On-Demand References pointing to runbook. | `CLAUDE.md` § On-Demand References |

### Anti-patterns

- Inline SQL panjang di chat untuk reset DB → bikin script.
- "Restart container, tunggu 30 detik, baru jalankan test" → script dengan health probe (lihat `rules/wait-patterns.md`).
- Helper exists tapi tidak ada runbook + CLAUDE.md ref → AI sesi baru tidak akan tahu helper-nya ada → tetap re-discover.
- Runbook tanpa TL;DR satu-baris-command — runbook yang butuh dibaca 2 menit kalah cepat dengan re-discovery.

---

## See also

- `rules/fr-contract-block.md` — L2 / L3 contract rules (single source for FR contract block + code-comment marker grammar)
- `rules/wait-patterns.md` — service-readiness wait patterns (HTTP probe, healthcheck, log scan)
- `agents/drift-triager.md` — post-drift classification agent
- `PROPOSAL_FOR_OTHER_PROJECTS.md` — adoption guide for adopting this pipeline + drift detector on a new project
