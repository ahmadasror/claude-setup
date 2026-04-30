# FR Contract Block Rule

Every FR file under `docs/fr/<module>/` that declares **at least one API endpoint, DB write, permission, or workflow definition reference** MUST include a machine-readable contract block as its **last section**. This block is the source of truth consumed by the drift detector binary that the project ships (e.g. `<project>-drift`).

## Section format

```markdown
## NN. Contract (machine-readable)

> Drift-detector source. Do not duplicate human content above. Schema:
> `docs/fr/_contract-schema.json`. Validation runs in CI.

```yaml
fr_file: docs/fr/<module>/fr-<feature>.md
covers: [FR-<MODULE>-001, FR-<MODULE>-002]

prd_refs:                                # optional, additive (v2 Phase 4)
  - prd_file: docs/prd/<module>/index.md
    anchor: <slug-from-prd-anchors>      # must exist in PRD's anchors[];
                                          # use 'full-prd' if no fine-grained anchors

permissions:
  declared: [<perm.string>, ...]
  consumed: [<perm.string>, ...]

endpoints:
  - method: POST
    path: /api/v1/...
    auth: { mode: jwt, permission: <perm.string> }
    responses: { 200: {...}, 400: {...} }
    audit: { action: create, resource_type: <entity>, meta_tags: [...] }
    idempotency: { natural_key: [...] }

db:
  reads: [<table>, ...]
  writes:
    - { table: <table>, columns_declared: [...], uniques: [{ cols: [...], predicate?: <where> }] }

enums:
  <table>.<col>: [VALUE_A, VALUE_B, ...]

workflow_definitions:
  - file: <repo-relative-path>/<workflow>.yaml
    asserted: { step_count: N, steps: [{ order: 1, role: <role>, deadline: <duration> }, ...] }

cross_links:
  consumers: [{ fr: <path>, ac: <id> }]
  sisters: [<path>, ...]
```
```

The fenced YAML block is parsed by the project's drift detector and validated against `docs/fr/_contract-schema.json`. CI fails if:
- The block is missing on an FR that declares endpoints/writes/permissions
- The block is schema-invalid
- A claim diverges from code/DB/workflow reality (Phase 2: blocking; Phase 1: warning)

## Authorship

- **fr-writer** generates the block as part of FR output (see `~/.claude/agents/fr-writer.md` Step 7).
- **Existing FRs** are backfilled by a one-shot generator script (e.g. `scripts/build-fr-contract-blocks.py`) — output is then human-reviewed before merge.
- **Updates** happen at the same PR as the underlying FR change. Do not let the block drift from human-readable sections — the human content is documentation, the YAML block is contract.

## What goes in the block vs the human sections

| Belongs in YAML block | Belongs in human sections |
|---|---|
| endpoint method/path/auth | API rationale, why this status code |
| permission strings | RBAC explanation, who-can-do-what narrative |
| DB tables & column lists | Data model diagrams, lifecycle narrative |
| enum value lists | enum semantics, transition rules |
| workflow file path + step count | step-by-step narrative, business rules |
| cross-link file paths | consumer relationship rationale |

The block is a **claim**, not a tutorial. Keep it tight; narrative & rationale stay in `## Functional Requirements`, `## Business Rules`, `## Data Model Touch Points`.

## In-scope modules (Phase 1)

The drift detector enforces this block on **mature** modules — those whose FR layer is stable and whose code is in production. Each project picks its in-scope set and lists it in `<project>-drift`'s default config.

Out-of-scope modules (Phase 2): pre-FR or actively-evolving modules where the human FR layer is still churning. Promote a module from Phase 2 → Phase 1 once its FR layer settles.

## Waivers

Phase 2 mechanism (not enforced in Phase 1). When code intentionally diverges from FR temporarily (e.g. FR ahead of code waiting on PR):

```yaml
cross_links:
  waivers:
    - rule: endpoints
      until: 2026-05-15
      reason: "Endpoint X scheduled for FR-<MODULE>-073 sprint, lands by 2026-05-15"
```

After `until`, drift detector fails again unless the waiver is renewed or the underlying drift is resolved.

## v2 sister contract blocks — the 5-link spine

The FR contract block (above) is **link L2** in the v2 traceability spine. Four sister contract surfaces extend coverage to L1, L3, L4, L5. They are documented separately but co-evolve with this rule:

| Link | Source-of-truth | Schema | Block heading |
|---|---|---|---|
| L1 PRD → FR | `docs/prd/<module>/**/*.md` | `docs/prd/_contract-schema.json` | `## NN. PRD Contract Block (machine-readable)` |
| L2 FR → code/DB/wf | `docs/fr/<module>/*.md` | `docs/fr/_contract-schema.json` | `## NN. Contract (machine-readable)` ← this rule |
| L3 code → FR (comment) | `*.go` / `*.java` source | regex grammar (no JSON Schema) | leading doc-comment marker |
| L4 FR → test scenario | `docs/test-scenarios/<module>/{flow,api,fe}/*.md` | `docs/test-scenarios/_contract-schema.json` | `## NN. Test Contract Block (machine-readable)` |
| L5 scenario → result | `docs/test-reports/_ratchet/<scope>-state.json` | `docs/test-reports/_ratchet-schema.json` | not a markdown block — JSON state file |

Full design lives in the project at `docs/architecture/drift-detector/v2-traceability-spine-design.md`.

### `prd_refs[]` (additive — v2 Phase 4)

The FR contract block's optional `prd_refs[]` field back-links each FR to a PRD anchor. Present in `docs/fr/_contract-schema.json` as additive (FRs without `prd_refs` still validate). When set, the differ flags `fr_orphan_prd_ref` if the cited PRD or anchor is missing.

```yaml
prd_refs:
  - prd_file: docs/prd/<module>/index.md
    anchor: <anchor-slug>            # must exist in PRD `anchors[]`
  - prd_file: docs/prd/<module>/index.md
    anchor: full-prd                  # reserved slug for whole-PRD reference
```

Skip the field for FRs that have no PRD ancestor. fr-writer authors `prd_refs[]` opportunistically when the PRD has populated anchors; backfill is Phase 4.2.

---

## Code-Comment FR-Marker Convention (link L3 — sister rule)

> Sister rule to the FR contract block above — both must hold for v2 spine compliance.

### Rule

Every **public method** on type matching `*Handler|*Service|*Repository|*Controller` (Java) or any exported func in `internal/{handler,service,repository,middleware}/` (Go) for in-scope modules MUST have a **leading doc-comment** containing one of the following markers:

| Marker | Semantics |
|---|---|
| `FR-<MODULE>-<NNN> [AC-<N>]` | Real reference. Prefix segments accept `[A-Z]{2,15}` (e.g. `FR-008`, `FR-MOD-008`, `FR-MOD-NAME-001`). AC suffix accepts `AC-N` flat or `AC-NNN-N` compound. Multiple markers per method are valid. |
| `FR-TBD` | Time-boxed placeholder — escalates to `marker_missing` (P1) after 90-day TTL via the ledger at `docs/drift-reports/_marker-state.json`. |
| `audit:skip — <reason>` | Intentional non-emit on a CUD path. Reason is mandatory. |
| `fr:internal` | Method has no user-facing surface (cache helper, internal RPC, etc.). |
| `fr:exempt — <reason>` | Intentional gap with reference (ADR id, ticket, or follow-up FR). |

Precedence (first match wins): `FR > TBD > SKIP > EXEMPT > INTERNAL`.

### Placement constraint (D2 — leading-only)

The marker MUST be in the leading doc-comment immediately above the method declaration:

- **Java**: inside the `/** ... */` Javadoc that precedes the method (allow `@Annotation` lines between Javadoc close and method signature).
- **Go**: in the `//` comment lines immediately above `func`, no blank line between comment and `func`.

Mid-method comments and trailing comments do **not** count. The scanner uses `*ast.FuncDecl.Doc` (Go) and a 60-line lookback window (Java) — Javadoc bodies longer than 60 lines either need to be split or relocated, otherwise they're flagged `javadoc_too_long` (P2).

### Enforcement

- **Extractor**: `code_comment` in `<project>-drift check`. Opt-out via `--skip-extractor code_comment`.
- **Strict mode**: a Makefile target like `make drift-strict` runs `--strict-modules <list>` — drift entries from those modules return non-zero (P0/blocking). Other in-scope modules are warning-only pending CI promotion.
- **Auto-stub**: `bash scripts/fr-tbd-stub.sh --module <m>` seeds `FR-TBD` placeholders idempotently on missing markers (Java + Go separately handled). Doc-comment edits only — never touches executable code.
- **TTL ledger**: `docs/drift-reports/_marker-state.json` records when each `FR-TBD` was first seen. Differ escalates to `marker_missing` (P1) at day 90.

### Backfill bucket convention

When migrating an unmarked module, classify each method into one of five buckets BEFORE editing:

| Bucket | Meaning | Marker added |
|---|---|---|
| **B1** | FR-AC mapped — method maps cleanly to an existing FR-AC pair | `FR-<MOD>-<NNN> AC-<N>` |
| **B2** | `fr:internal` — no user-facing surface | `fr:internal` |
| **B3** | `fr:exempt-known` — superseded / intentional gap with reference | `fr:exempt — <ref>` |
| **B4** | FR-gap — method exists but no FR captures it yet | `fr:exempt — see FR_GAPS.md` (then fr-writer follow-up) |
| **B5** | Time-boxed unknown | `FR-TBD` (90d TTL) |

Triage FIRST (~30 min per module — read each method's purpose, classify), edit SECOND (mechanical add of the marker). Skipping triage produces inconsistent marker pairs (handler+service referencing different FR-ACs) — handler claims `FR-X AC-1`, the service it calls claims `FR-Y AC-3`, drift detector flags both, you fix one, the other surfaces next run, etc.

### In-scope modules

Each project lists its current in-scope set (Phase 1: strict, Phase 2: warning-only, Phase 2.5: adjacency). Pending modules stay Phase 3 — drift detector skips them entirely until ready.

---

## See also

- FR schema: `docs/fr/_contract-schema.json` (incl. `prd_refs[]`)
- PRD schema: `docs/prd/_contract-schema.json`
- Test scenario schema: `docs/test-scenarios/_contract-schema.json`
- Ratchet schema: `docs/test-reports/_ratchet-schema.json` + `_results-schema.json`
- Drift detector binary: `<repo>/cmd/<project>-drift/` (Go-based; concepts port to any language)
- Result normalizer: `scripts/normalize-pw-results.sh`
- Auto-stub: `scripts/fr-tbd-stub.sh`
- Agent — drift-triager: `agents/drift-triager.md`
- Agent — fr-writer override: `agents/fr-writer.md`
- Agent — pimpro override: `agents/pimpro.md`
