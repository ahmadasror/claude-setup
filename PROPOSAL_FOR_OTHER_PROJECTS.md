# Proposal — Adopting This Pipeline on a New GitHub Project

> Praktisi tone, Indonesian-mix narrative + English structured fields. The pipeline + drift detector + 5-link spine described here was battle-tested on a non-trivial product codebase (~75+ features across 8 modules, mixed Go + Java + Nuxt). This doc distills the adoption path so a new project can pick it up in phases without bringing the whole estate from day 1.

> ⚠️ **Read `AGENT_WORKFLOW.md` §SDD Lean Mode first.** The same battle-tested codebase
> later **retired most of this heavy spine** — it proved too heavy for a solo-operator +
> AI loop (CI stopped firing, drift became a firehose, the marker ledger sat empty).
> The operative practice is now 3 artifacts (FR + contract block, ADR, green tests) with
> drift **advisory** on critical paths. Treat the phases below as an **à la carte menu**:
> start from Lean Mode (Phase 1 + the FR contract block) and add a later layer **only
> when it pays rent**. Adopting all 5 spine links on day 1 is exactly the over-weight
> mistake this warning exists to prevent.

---

## TL;DR

You get:
- **8 pipeline agents** + **4 supporting agents** that take you from user intent → PRD → architecture → FR → test scenarios → code + unit tests → Playwright + report → status dashboard.
- **6 global rules** that bind agents to consistent outputs (audit, git, security, testing, FR contract block, wait patterns).
- **5-link traceability spine** that ties PRD ↔ FR ↔ code ↔ test scenario ↔ test result. A drift detector binary you ship in your own repo reads all 5 surfaces and reports inconsistency.
- **Per-tier test ratchet** that catches green→red regressions across runs without false positives from scope shrinkage (T1 ⊂ T2).
- **Event-driven status dashboard** (pimpro mode A) that doesn't re-read your whole repo on every agent completion.

You DO get a turnkey drift detector binary — published as a separate public repo at **https://github.com/ahmadasror/drift-detector**. Single Go binary, MIT, ships all 5 schemas + reference examples. Adopt it via `go install github.com/ahmadasror/drift-detector/cmd/drift-detector@latest`. This proposal walks the contracts and adoption phases; the binary is the canonical implementation. Adopters can fork + extend if their stack needs custom extractors, but a vanilla install covers the v2 spine 5-link checks out of the box.

---

## Table of Contents

1. [Why this matters](#1-why-this-matters)
2. [What you get](#2-what-you-get)
3. [Phase 0 — Repo bootstrap](#phase-0--repo-bootstrap-1-hour)
4. [Phase 1 — Adopt agent pipeline](#phase-1--adopt-agent-pipeline-1-2-weeks-per-module)
5. [Phase 2 — Adopt drift detector](#phase-2--adopt-drift-detector-2-4-weeks)
6. [Phase 3 — Code-Comment Marker (L3)](#phase-3--code-comment-marker-l3-1-week-per-module)
7. [Phase 4 — Test Scenario + Ratchet (L4 + L5)](#phase-4--test-scenario--ratchet-l4--l5-1-2-weeks)
8. [Phase 5 — PRD Contract Block (L1)](#phase-5--prd-contract-block-l1-1-week)
9. [Required infrastructure](#9-required-infrastructure)
10. [Common pitfalls](#10-common-pitfalls)
11. [Why per-tier ratchet matters](#11-why-per-tier-ratchet-matters)
12. [Roadmap from "0 spine" → "5/5 spine"](#12-roadmap-from-0-spine--55-spine)

---

## 1. Why this matters

If you've worked on a project longer than a few months you've probably seen these failure modes:

- **PRD says one thing, FR says another, code does a third, tests verify the fourth.** Any single layer might be correct in isolation, but together they slowly drift.
- **A test passes, then six months later it's silently skipped** because someone refactored the seed and the precondition no longer matches. Nobody notices until production breaks.
- **A PR adds a new endpoint, but the FR docs never get updated.** Two months later, somebody else on the team thinks the endpoint doesn't exist and re-implements it.
- **An "acceptance criterion" in the FR has no test case.** The team just trusts that "we tested that manually once."

The 5-link spine fixes this not by adding more docs but by making each link **machine-checkable**:

| Question | Spine link that answers it |
|---|---|
| "Does our PRD list every FR that implements it?" | L1 PRD → FR (PRD Contract Block) |
| "Does every FR endpoint claim match a real handler?" | L2 FR → code (FR Contract Block) |
| "Does every public method have an FR-AC backreference?" | L3 code → FR (code-comment marker) |
| "Does every FR-AC have a test case covering it?" | L4 FR → scenario (Test Scenario Contract Block) |
| "Did any green test go missing or fail today?" | L5 scenario → result (per-tier ratchet) |

A single binary checks all 5. You wire it as a CI gate. Drift becomes a pull-request blocker, not a slow surprise.

---

## 2. What you get

### Agents (12 total)

**Pipeline (8)** — one main flow:

```
requirement-gatherer ─→ architect (3 modes) ─→ fr-writer ─→ tester-explorer ─→ test-builder + night-builder
                                                                                      │
                                                                                      ▼
                                                                                   pimpro
                                                                                      │
                                                                                      ▼
                                                                              drift-triager (post-drift)
```

**Supporting (4)** — invoked on-demand: `architect-financial`, `planner`, `presenter`, `security-reviewer`.

### Rules (6)

- `audit.md`, `git-workflow.md`, `security.md`, `testing.md` — generic engineering rules.
- `fr-contract-block.md` — L2/L3 contract surfaces.
- `wait-patterns.md` — service readiness anti-patterns and reliable patterns.

### Workflow contracts (cross-agent)

Documented in `AGENT_WORKFLOW.md`:
- **5-link traceability spine** — the core invariant.
- **UI Selectors** — `data-testid` is a published API across fr-writer / night-builder / tester-explorer / test-builder.
- **FR Contract Block (L2)** — drift detector source of truth for endpoints/permissions/DB writes.
- **Code-Comment Marker (L3)** — every public method on `*Handler|*Service|...` has leading FR-AC marker or sentinel (`audit:skip`, `fr:internal`, `fr:exempt`, `FR-TBD`).
- **Test Scenario Contract Block (L4)** — every TC traces to ≥1 FR-AC.
- **Test Result Ratchet (L5)** — per-tier state files prevent scope-shrinkage false positives.
- **PRD Contract Block (L1)** — PRD declares which FRs implement it.
- **Test Tiering** — T0 / T1 / T2 / T3 with mechanical Playwright tag application.

### Sample artifacts

`samples/01-requirement-gatherer/` … `samples/07-pimpro/` walk the same fictional `orders` module through every agent. (Sample 08 — drift-triager — is added with this proposal.)

---

## Phase 0 — Repo bootstrap (1 hour)

### Setup user-global agent profile

```bash
cd ~
git clone git@github.com:<your-fork>/claude-setup.git
mkdir -p ~/.claude/agents ~/.claude/rules
cp claude-setup/agents/*.md ~/.claude/agents/
cp claude-setup/rules/*.md  ~/.claude/rules/
# Review settings.json before copying
cp claude-setup/settings.json ~/.claude/settings.json
```

Now any project gets the same agent definitions out of the box.

### Set up project-level overrides

In your target project repo:

```bash
mkdir -p .claude/agents .claude/rules
```

Per-project overrides go in `.claude/agents/<agent>.md` and `.claude/rules/project-overrides.md`. The override pattern: read the user-global agent first for Steps 1–N, then apply additions/changes for project specifics. Example: a project on Java + Spring Boot puts JVM-specific notes in `.claude/agents/test-builder.md` (waitForActuator), not in the global file.

### Bootstrap project skeleton

Minimum directories (create as you go, not all at once):

```
docs/
├── prd/<module>/                    # requirement-gatherer output
├── architecture/<module>/           # architect output
│   └── adr/                         # individual ADRs
├── fr/<module>/                     # fr-writer output (+ contract block when ready)
├── test-scenarios/<module>/{flow,api,fe}/   # tester-explorer output
├── test-reports/                    # test-builder + ratchet
│   └── _ratchet/                    # per-tier state files (Phase 4)
├── night-builds/                    # night-builder reports
├── drift-reports/                   # drift detector output (Phase 2+)
├── discovery/                       # requirement-gatherer journal
└── pimpro/                          # status dashboard
    ├── status.md                    # canonical
    └── agent-log.jsonl              # event-driven feed (mode A)
```

You don't need all of these on day 1. Start with `docs/discovery/` and `docs/prd/` — that's the first agent's only target.

### Add CLAUDE.md

Per-project `CLAUDE.md` should declare:
- Tech stack (so agents know which language conventions apply)
- Service URLs / ports for local dev
- Default credentials or where they live (env file paths)
- Domain vocabulary mapping (folder name ≠ business name)
- Pipeline focus right now (which module is active)

---

## Phase 1 — Adopt agent pipeline (1-2 weeks per module)

Pick **one** module to start. Don't try to bring 8 modules through the pipeline simultaneously — you'll burn out.

### Step 1: requirement-gatherer

```
Prompt: "Buat PRD untuk modul <module>"
```

Output:
- `docs/discovery/<date>-<topic>.md` — research journal
- `docs/architecture/domains/index.md` — domain map
- `docs/prd/<module>/index.md` — PRD index with Flow Map
- `docs/prd/<module>/<workflow>.md` — per-workflow PRD

PRD Contract Block (L1) is **optional** at this stage — add it in Phase 5.

### Step 2: architect Mode 1

```
Prompt: "Solution design untuk modul <module> dari docs/prd/<module>/ — Mode 1, output design.md"
```

Output: `docs/architecture/<module>/design.md` (strategic design — bounded context, entity model, NFR, integration patterns) + ADRs.

### Step 3: fr-writer

```
Prompt: "Buat FR untuk modul <module> dari docs/prd/<module>/"
```

Output:
- `docs/fr/<module>/index.md` — epic breakdown
- `docs/fr/<module>/fr-<workflow>.md` — ticket stubs + AC + API response codes + UI Selectors section
- `docs/fr/<module>/completion-status.md` — open questions

FR Contract Block (L2) is **deferred to Phase 2** — first iteration of FRs can be written without it.

### Step 4: architect Mode 2

```
Prompt: "Technical spec untuk modul <module> dari docs/fr/<module>/ — Mode 2, output api-spec.md"
```

Output: `docs/architecture/<module>/api-spec.md` (API contracts derived from FR + design).

### Step 5: tester-explorer

```
Prompt: "Explore domain <module>"
```

Three phases (P1: state machine + AC log; P2: seed data map; P3: test scenarios with Tier annotation). Output: `docs/test-scenarios/<module>/{flow,api,fe}/*.md`.

Test Scenario Contract Block (L4) is **deferred to Phase 4** — first scenarios can be written without it.

### Step 6: implement (night-builder + test-builder in parallel)

```
# night-builder (autonomous overnight; does code + unit tests)
Prompt: "Implement <FR-IDs> dari docs/fr/<module>/fr-<workflow>.md"

# test-builder (Playwright generation + run + report)
Prompt: "Build <module> F-01..F-N, all flows"
```

Note: night-builder reads test scenarios as a validation contract — they must exist before night-builder runs.

### Step 7: pimpro

Configure a `SubagentStop` hook in `.claude/settings.json` that appends one JSONL line per agent completion to `docs/pimpro/agent-log.jsonl`. Pimpro mode A picks up from there.

```bash
# Manual trigger for a full status dashboard
Prompt: "pimpro full scan"
```

### Done — what does Phase 1 buy you?

- All artifacts in standard places. Future agents on the same project can find them.
- Test code generated mechanically from scenarios. Renames stay consistent.
- Status dashboard tells you (and your team) where every module sits in the pipeline.
- **Zero drift detection yet.** That's Phase 2.

---

## Phase 2 — Adopt drift detector (2-4 weeks)

This is where you build the L2 FR → code drift binary in your project.

### What the binary does

Reads the FR Contract Block YAML, then for each module:
1. Walks Go/Java handler/service code, extracts every endpoint route.
2. Walks DB migrations, extracts every CREATE TABLE / ALTER TABLE / CREATE INDEX.
3. Walks workflow definition YAMLs (if you use a workflow engine like LightWorkflow, Temporal, etc.).
4. Walks permission constants files.
5. Compares each FR Contract Block claim against the extracted reality.
6. Emits a JSON report with one entry per drift, classified by `kind` and `reason`.

**Recommended path — install the canonical binary**:

```
go install github.com/ahmadasror/drift-detector/cmd/drift-detector@latest
drift-detector --help
```

The repo at https://github.com/ahmadasror/drift-detector ships:
- All 5 JSON schemas in `schemas/` (FR + test-scenarios + PRD + test-results + ratchet)
- Working extractors for Go (Gin) + Java (Spring) + Postgres + Workflow YAML + permissions + code-comment + test-scenario + test-result + PRD
- 105 passing tests, 14MB single static binary
- Examples in `examples/` (FR + test-scenario + PRD samples)

Copy the schemas into your repo at `docs/fr/_contract-schema.json` etc. Configure the binary's in-scope module list via the `inScopeModules` map in your fork (or via `--module` flags — see `--help`).

**Alternative — fork + extend**: if your stack needs custom extractors (e.g. Python FastAPI routes, Rust Axum, GraphQL schema), fork https://github.com/ahmadasror/drift-detector and add an extractor under `internal/drift/extractor/`. The reporter + differ + parser are stack-agnostic.

**Hard parts** (regardless of path):
- **Endpoint extraction** — regex on `r.Get("/api/v1/...")` for stdlib router; Spring `@RequestMapping` annotations for Java. The canonical binary handles both.
- **DB schema extraction** — parse `migrations/*.sql` files; track ON CONFLICT clauses to bind to unique constraints (see `migration-discipline.md` rule).
- **Workflow YAML** — straight YAML parse + step count + role assertion.

Reference design: copy `docs/ARCHITECTURE.md` from the drift-detector repo to your project's `docs/architecture/drift-detector/design.md`. Genericize the example modules to your domain.

### Step-by-step

**Week 1 — schemas + extractors**

- Author `docs/fr/_contract-schema.json` (JSON Schema for the FR Contract Block).
- Pick **one** in-scope module (e.g. the smallest, with FRs you trust). Author its FR Contract Block by hand following `rules/fr-contract-block.md`.
- Build the binary's endpoint extractor (~500 LOC) + JSON output.
- Run binary against the one module → emit drift report.

**Week 2 — wire CI**

- Add `make drift-validate` (schema validation only, no DB).
- Add `make drift-check` (full extractor pass, possibly needs DB).
- Add `.github/workflows/drift-check.yml` (PR gate, read-only):

```yaml
name: drift-check
on: pull_request
jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
      - run: make drift-validate    # schema validation
      - run: make drift-check       # extractor pass — Phase 1: warning, Phase 2: blocking
```

**Week 3 — backfill module by module**

- For each in-scope module, run a one-shot generator script (`scripts/build-fr-contract-blocks.py`) that parses existing FR markdown tables → seeds YAML skeleton with TODO markers. Human reviews + completes each block.
- Each module's first PR backfilling its blocks is its own PR — easier to review.

**Week 4 — promote to strict**

- Once all in-scope modules have valid blocks and zero drift, set `--strict-modules <list>` in CI. Drift in those modules now blocks PRs (P0/exit-non-zero).

### drift-triager workflow

After every drift detector run:

```
Prompt: "Triage latest drift report"
```

Output: `docs/drift-reports/YYYY-MM-DD-triage.md` with classification per entry. User dispatches fixes:
- FR-ahead → `night-builder` (implement to match FR)
- Code-ahead → `fr-writer` (extend FR to cover new surface)
- Real-mismatch → manual_review (human decides canonical side)
- Waiver-eligible → accept (drift is intentional, expiry tracked)

---

## Phase 3 — Code-Comment Marker (L3) (1 week per module)

L3 closes the loop the other direction: from code back to FR. Every public method on `*Handler|*Service|*Repository|*Controller` (Java) or exported func in `internal/{handler,service,repository,middleware}/` (Go) MUST have a leading doc-comment with one of: `FR-X AC-Y` / `audit:skip — reason` / `fr:internal` / `fr:exempt — reason` / `FR-TBD`.

### Bootstrap workflow per module

**Day 1: triage (read-only, no code edits)**

For each method in scope, classify into one of 5 buckets:

| Bucket | Meaning | Marker |
|---|---|---|
| **B1** | FR-AC mapped — clear FR-AC pair | `FR-<MOD>-<NNN> AC-<N>` |
| **B2** | Internal helper — no user-facing surface | `fr:internal` |
| **B3** | Superseded / intentional gap with reference | `fr:exempt — <ref>` |
| **B4** | FR-gap — method exists but no FR captures it | `fr:exempt — see FR_GAPS.md` (then fr-writer follow-up) |
| **B5** | Time-boxed unknown | `FR-TBD` (90d TTL) |

Triage produces a markdown table in `docs/drift-reports/<module>-bucket-triage.md`.

**Day 2-3: edit (mechanical — apply markers)**

For each row in the triage table, add the leading doc-comment. ~30 minutes per module of triage + 1-2 hours of mechanical edit.

**Day 4: extractor + drift report**

- Build `code_comment` extractor in `<project>-drift` (~500 LOC). Go uses `go/parser` + `*ast.FuncDecl.Doc`. Java uses 60-line lookback (Javadoc + `@Annotation` lines).
- Run extractor → 0 drift entries expected.

**Day 5: promote to strict mode**

`make drift-strict` runs `--strict-modules <m>` on the cleaned modules.

### Auto-stub for new modules

`bash scripts/fr-tbd-stub.sh --module <m>` seeds `FR-TBD` placeholders idempotently — useful when bringing a new module into L3 quickly. Doc-comment edits only, never touches executable code. The `_marker-state.json` ledger tracks first-seen date; differ escalates to `marker_missing` (P1) at day 90.

### When fr-writer fails to give you an AC

If a method has no obvious FR-AC pair, your triage should resolve to one of B3, B4, B5 — never B1 with a guessed FR. B5 (`FR-TBD`) buys you 90 days to author the missing FR; after that the marker escalates to `marker_missing` and CI starts pressuring.

---

## Phase 4 — Test Scenario + Ratchet (L4 + L5) (1-2 weeks)

L4 ties FR-AC to test cases. L5 catches green→red regressions across runs.

### L4 — Test Scenario Contract Block

Author `docs/test-scenarios/_contract-schema.json`. Then for each scenario file under `docs/test-scenarios/<module>/{flow,api,fe}/*.md`, append a Test Contract Block:

```yaml
ts_file: docs/test-scenarios/<module>/api/flow-NN-<name>.md
layer: api
covers: [TC-MOD-001-HP-001, ...]
tcs:
  - id: TC-MOD-001-HP-001
    title: HR submits valid form
    traces_to: [FR-MOD-001 AC-1]
    type: HP
cross_links:
  fr_files: [docs/fr/<module>/fr-<feature>.md]
```

The L4 differ checks:
- Every TC in `tcs[]` has at least one entry in `traces_to[]` (else `tc_orphan` P2).
- Every FR-AC pair in `traces_to[]` exists in some FR Contract Block (else `traces_to_unknown_fr/ac`).
- Every FR-AC has at least one TC tracing to it (else `ac_uncovered` P1).

If a TC genuinely cannot be tested (NFR like "system shall be performant"), set `test_coverage: { required: false }` on the FR-AC so it falls to P2.

### L5 — Per-tier ratchet

Each tier has its own state file:

| Tier | Scope | State file |
|---|---|---|
| T0 smoke | `smoke` | `_ratchet/smoke-state.json` |
| T1 critical (per module) | `<module>-t1` | `_ratchet/<module>-t1-state.json` |
| T2 full (per module) | `<module>-t2` | `_ratchet/<module>-t2-state.json` |

Pipeline:

```bash
make test-t0
  ├─ npx playwright test --grep @t0
  ├─ bash scripts/normalize-pw-results.sh --scope smoke
  │   └─ writes docs/test-reports/<run-id>-smoke-results.json
  └─ <project>-drift check --ratchet-scope smoke --ratchet-update
      └─ updates docs/test-reports/_ratchet/smoke-state.json (rolling N=10)
```

The differ emits 4 kinds:

| Kind | Severity | Trigger |
|---|---|---|
| `regression` | **P0** | `passed → failed` or `passed → timed_out` |
| `silent_drop` | P1 | `passed → missing` (state had it, latest run doesn't) — check tier-mismatch first |
| `green_streak_broken` | P1 (additive) | TC was green for ≥5 consecutive runs and flipped |
| `tc_unknown` | P2 | Test title carries TC pattern but no L4 block declares it |

### CI red line — PR jobs never mutate ratchet state

| Stage | Mode |
|---|---|
| **PR gate** (`drift-check.yml`) | Read-only — never `--ratchet-update`. PR runs allowed to mutate state would whitewash regressions. |
| **Nightly** (`drift-nightly.yml`) | Mutates state via `--ratchet-update` after canonical run. |

This is the single most important rule for L5. Get it wrong and the ratchet becomes a noisy pacifier instead of a regression net.

---

## Phase 5 — PRD Contract Block (L1) (1 week)

L1 closes the back-end of the spine — PRD declares which FRs implement it; FR optionally back-links to PRD anchor.

Author `docs/prd/_contract-schema.json`. Then for each mature PRD, append:

```yaml
prd_file: docs/prd/<module>/index.md
status: approved
last_review_date: 2026-04-30
owner: <product team>
covers: [FR-MOD-001, FR-MOD-002, ...]
anchors:
  - id: <anchor-slug>
    title: "§3 <Section title>"
cross_links:
  fr_files: [docs/fr/<module>/fr-<feature>.md, ...]
```

Once the PRD has `anchors[]`, fr-writer can opportunistically declare `prd_refs[]` in FR Contract Blocks back-linking to anchor slugs. Differ flags `fr_orphan_prd_ref` (P2) if the cited PRD or anchor is missing.

L1 is **last** in the adoption order because it's the cheapest to delay — you can run the pipeline + L2-L5 cleanly without ever touching PRD blocks. But once you have it, drift detector flags PRDs whose `covers[]` list references missing FRs (`prd_orphan_fr` P1) — which is the surface that catches "we claimed this PRD is done but FR-XYZ never got written."

---

## 9. Required infrastructure

### Drift detector binary

- **Language**: Go is what the reference implementation uses. The concepts port to any language. ~3-5kLOC for a basic 5-extractor implementation.
- **Distribution**: built per-project, lives at `<repo>/cmd/<project>-drift/`. Make a `make build-drift` target.
- **Inputs**: contract schema files, FR/PRD/scenario markdown, source code, DB migrations, workflow YAMLs.
- **Outputs**: `docs/drift-reports/<date>/report-drift.json` (dated subdir layout).

### Test runner with structured output

- Playwright with `--reporter=list,'json:.pw-results.json'` (the JSON reporter is what the normalizer consumes).
- A normalizer script `scripts/normalize-pw-results.sh` that reads `.pw-results.json` + parses TC IDs from test titles → emits a normalized result file the drift detector consumes for ratchet update.

### Makefile orchestration

Recommended targets (per-project):

```makefile
drift-validate:    ## schema validation only — no DB
	./bin/<project>-drift validate

drift-check:       ## full extractor pass — may need DB
	./bin/<project>-drift check --output docs/drift-reports/$(shell date +%Y-%m-%d)/

drift-strict:      ## fail on drift in strict modules
	./bin/<project>-drift check --strict-modules <m1>,<m2>

test-t0:           ## smoke
	cd e2e && npx playwright test --grep @t0
	bash scripts/normalize-pw-results.sh --scope smoke
	./bin/<project>-drift check --ratchet-scope smoke --ratchet-update

test-<module>-critical:  ## T1 per module
	cd e2e && npx playwright test --grep @t1 --grep <module>
	bash scripts/normalize-pw-results.sh --scope <module>-t1
	./bin/<project>-drift check --ratchet-scope <module>-t1 --ratchet-update
```

### GitHub Actions

```yaml
# .github/workflows/drift-check.yml
name: drift-check
on: pull_request
jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
      - run: make drift-validate
      - run: make drift-check
      # PR runs are READ-ONLY against ratchet state — never --ratchet-update here

# .github/workflows/drift-nightly.yml
name: drift-nightly
on:
  schedule: [{cron: '0 2 * * *'}]   # 2am UTC daily
jobs:
  ratchet:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make test-t0    # mutates smoke ratchet
      - run: make test-<module>-critical    # mutates T1 ratchet
      # T2 included via include_t2: true input
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore(ratchet): nightly refresh"
          file_pattern: "docs/test-reports/_ratchet/*.json"
```

---

## 10. Common pitfalls

These came from the reference implementation's journey. You can save weeks by knowing them in advance.

### 10a. Skeleton-builder noise — don't auto-derive permissions from FR text

When backfilling FR Contract Blocks, you might be tempted to write a script that regex-extracts permission strings from the human-readable FR sections. Don't. Permission strings drift trivially in human-edited markdown (`payroll.lock` vs `payroll.locks` vs `Payroll.Lock`). The block must be **explicitly authored** so review catches typos. Use a backfill script only to seed the YAML skeleton with `# TODO` markers — humans fill in the actual values.

### 10b. Scope shrinkage in ratchet — need per-tier state files

If you store one global ratchet state file and run T1 (subset) on PR but T2 (superset) on nightly, the nightly run sees the T2-only TCs as `passed → missing` from the previous T1 run → false-positive `silent_drop` for ~every T2-only TC. The fix is per-tier scope files. The reference implementation hit this on day 3 of L5 and the per-tier design landed shortly after.

### 10c. Long Javadoc lookback bug — 60-line minimum

The Java code-comment extractor scans backward from a method declaration looking for a Javadoc start (`/**`). If your Javadoc is genuinely huge (legacy code), the lookback can stall. Reference implementation defaulted to 60 lines: anything longer triggers `javadoc_too_long` (P2) and the human has to either shorten the Javadoc or relocate the marker.

### 10d. Word boundary regex — `NFR-MOD-009` false-match

If your code-comment marker regex is `\bFR-[A-Z0-9-]+\b`, it'll match `NFR-MOD-009` (because `\b` matches between `N` and `F`). Use `(?:^|[^A-Z])FR-` or `(?:^|[\s/*])FR-` to anchor on a real boundary. The reference implementation hit this and shipped the fix early in Phase 3 backfill.

### 10e. CI mutating ratchet on PR

If your PR job runs `--ratchet-update`, every PR whitewashes its own regressions. The state file commits silently at PR merge. By the time someone notices a regression, the ratchet has already accepted it. Only nightly mutates state.

### 10f. Backfilling L3 markers without triage first

If you skip the bucket triage and go straight to "add a marker per method", you'll end up with handler+service pairs that reference different FR-ACs (handler claims FR-X AC-1, service it calls claims FR-Y AC-3). The drift report flags both, you fix one, the other surfaces next run. Triage FIRST (~30 min per module), edit SECOND.

### 10g. Forgetting to delete the flat `report-drift.json`

Initial drift detector output was at `docs/drift-reports/report-drift.json` (flat file). Once you switch to dated subdirs (`docs/drift-reports/<date>/report-drift.json`), DELETE the flat file — otherwise old tooling reads stale data forever. Pimpro and drift-triager should both resolve via `ls -t | head -1` against the dated dirs.

### 10h. Treating drift detector output as actionable on first run

First drift detector run on a real codebase will surface 100s of entries — most of which are FRs lagging behind code. That's normal. Use drift-triager to batch them (FR-ahead → night-builder, Code-ahead → fr-writer). Don't try to clear them all in one PR.

---

## 11. Why per-tier ratchet matters

This deserves its own section because it's the false-positive class fix that makes L5 useful.

### The naive design (one global ratchet)

```
ratchet-state.json
  tcs:
    - {tc_id: TC-MOD-001-HP-001, last_status: passed, ...}     # T1 + T2
    - {tc_id: TC-MOD-002-EDGE-001, last_status: passed, ...}   # T2 only
```

PR job runs `--grep @t1` → only TC-MOD-001 in results. Differ compares to baseline → TC-MOD-002 went missing → `silent_drop` P1 false positive. Every PR for every T2-only TC.

### The per-tier design

```
_ratchet/
  smoke-state.json      # smoke scope — 12 TCs
  <module>-t1-state.json # T1 scope — 80 TCs
  <module>-t2-state.json # T2 scope — 240 TCs (T1 ⊂ T2)
```

PR job runs `--grep @t1` → updates `<module>-t1-state.json` only. The T2-only TCs are in the T2 file, never compared against T1 results. No false positive.

If you collapse this back into one file, you re-introduce the bug. The per-tier scope is structural, not cosmetic.

---

## 12. Roadmap from "0 spine" → "5/5 spine"

Recommended order based on what gives you the most value-per-effort, smallest to largest:

| Order | Phase | Scope | Effort | Value |
|---|---|---|---|---|
| 1 | Phase 0 — bootstrap | Copy agents + rules to `~/.claude/`, set up project skeleton | 1 hour | Agents work consistently across projects |
| 2 | Phase 1 — pipeline (one module) | requirement-gatherer → fr-writer → tester-explorer → night-builder + test-builder for ONE module | 1-2 weeks | Standard doc layout; mechanical test gen |
| 3 | Phase 1 — pipeline (more modules) | Repeat for 2-3 more modules | 1-2 weeks each | Cross-module consistency |
| 4 | Phase 2 — drift detector L2 | Build binary, schema, FR Contract Block backfill for in-scope modules | 2-4 weeks | FR ↔ code drift caught at PR time |
| 5 | Phase 3 — code-comment L3 | Backfill markers, build extractor, promote to strict | 1 week per module | Code → FR drift caught; orphan code surfaced |
| 6 | Phase 4 — test scenario L4 | Author Test Contract Block per scenario file | 1 week | AC → TC coverage gap surfaced |
| 7 | Phase 4 — ratchet L5 | Per-tier state files, normalizer, CI red line | 1 week | Green→red regressions caught nightly |
| 8 | Phase 5 — PRD L1 | PRD Contract Block on mature PRDs | 1 week | PRD → FR drift caught (orphan FRs surfaced) |

**Total ramp-up to 5/5 spine, single module**: ~6-10 weeks. A team can run Phase 1 for one module while another team is doing Phase 2 for a different module — they don't block each other. The expensive bit is the binary build (~2-4 weeks) which only needs to happen once per project.

---

## Appendix A — language match (Indonesian / English)

The agent definitions and rules are bilingual — narrative is Indonesian-mix, structured fields (table headers, YAML keys, error codes) are English. Match the user's language in your invocations:

- "Buat PRD untuk modul payroll" → Indonesian narrative output
- "Generate FR for the orders module" → English narrative output

Both produce the same structured artifacts. Don't translate field names.

---

## Appendix B — when NOT to adopt this

Skip this whole proposal if:

- Your project is a 1-2 person spike that won't outlive 3 months — overhead exceeds value.
- You have no FR / PRD layer at all and don't plan to write them — drift detector has nothing to compare against.
- Your tests are unit-only (no E2E) — the L5 ratchet has nothing to ratchet.
- You're a research codebase where breaking changes are expected weekly — FR layer would constantly churn.

Adopt selectively if:

- You're a 3-10 person team on a multi-month commercial product with real users → all 5 links pay for themselves within 6 months.
- You've already written FRs as docs and want to keep them honest → start with Phase 2 only, skip the rest until you feel pain.
- You have a flaky regression problem you can't pin down → skip to Phase 4 ratchet alone; gives you 80% of the spine value at 20% of the cost.

---

## See also

- `AGENT_WORKFLOW.md` — pipeline + cross-agent contracts (5-link spine, UI Selectors, FR Contract Block, Code-Comment Marker, Test Scenario Contract Block, Test Result Ratchet, PRD Contract Block, Test Tiering)
- `rules/fr-contract-block.md` — L2/L3 rule
- `rules/wait-patterns.md` — service readiness
- `agents/drift-triager.md` — post-drift classification
- `samples/` — end-to-end fictional `orders` module walking the pipeline
