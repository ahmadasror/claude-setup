# Claude Setup — Global Agent Config

This repo mirrors the agent definitions and rules from `~/.claude/`.

> **Source of truth for pipeline order, inputs/outputs, and cross-agent contracts**: `AGENT_WORKFLOW.md`. Anything here that conflicts with that doc is stale — update or delete.

> **Operative practice = SDD Lean Mode** (`AGENT_WORKFLOW.md` §SDD Lean Mode). The
> mandatory surface is 3 artifacts (FR + contract block, ADR, green tests); the heavy
> spine + 8-agent pipeline documented below is **reference / opt-in**. `pimpro` is
> retired. Cross-repo work uses `CROSS_REPO_HANDOFF.md`. The "Agent Design Decisions"
> notes below predate Lean Mode and describe agents in their full-pipeline role — read
> them as design rationale, not as a mandatory run order.

## Sync Convention

One-way: `~/.claude/` is the live copy, this repo is the mirror.

```bash
# After editing ~/.claude/agents/*.md locally
cp ~/.claude/agents/*.md agents/
git diff   # review before commit
```

For repo → `~/.claude/` (onboarding a new machine), see `README.md` § Install.

---

## Agent Design Decisions

### tester-explorer

**Status**: Active — being iterated

**Purpose**: QA intelligence agent. Reads domain docs, extracts state machines and workflows, maps seed data needs, then generates test scenarios. Output drives both manual and automated test execution.

**Position in agent flow**:
```
requirement-gatherer → PRD
architect [Mode 1]   → design.md (strategic)
fr-writer            → Epics + Ticket stubs with AC
architect [Mode 2]   → api-spec.md (technical contract)
tester-explorer      → Test scenarios  ← here
```

**Design decisions**:

1. **3-phase with 2 checkpoints** — not a single linear run
   - Phase 1: Workflow + state machine extraction → user confirms correctness
   - Phase 2: Seed data discovery → user confirms completeness
   - Phase 3: Test scenario generation
   - Rationale: wrong state machine = wrong everything downstream. Checkpoints catch this early.

2. **Output to a single progressive file, not conversation**
   - File: `tester-{domain}-{YYYY-MM-DD}.md` in project root or `/test-scenarios/`
   - Each phase appends its section to the same file
   - Rationale: agent re-invocation starts blank — file is the only persistent state. User can also edit the file directly between phases.

3. **Pickup from mid-stage via file detection**
   - On re-invocation, agent reads the existing `tester-{domain}-*.md` file
   - Detects which sections are present (State Machine / Seed Data Map / Test Scenarios)
   - Continues from the next missing phase automatically
   - Rationale: user may correct state machine, re-run Phase 2 without redoing Phase 1

4. **Monolith doc over sub-docs**
   - All phases written to one file with clear `## Phase N` section headers
   - Rationale: AI reads one file in full context; sub-docs require navigation and risk missing pieces. Humans also prefer structured single doc with TOC over scattered files.

5. **Scenario ID format**: `{DOMAIN}-{CATEGORY}-{NNN}` e.g. `TRANSFER-HP-001`

6. **12 test categories** (+ 4 core banking bonus):
   - HP, SP, ST, STX, BR, AUTH, IDEM, CONC, EDGE, INT, AUDIT, COMP
   - Core banking: REG, LEDG, RECON, FORENS

7. **Coverage matrix** mandatory — every AC line must map to ≥1 scenario ID or be flagged as gap

**Known bumps when applying to financial/clearing domains**:
- fr-writer must run first — no AC = no traceability
- State machines in clearing/settlement are DAGs not chains — STX scenarios explode
- Seed data for timing-dependent scenarios (T+N settlement windows) can't be expressed statically
- External rails (BI-FAST, SKN, RTGS) behavior on failure is underdocumented — flag as assumption
- Maker-checker × batch = complex CONC preconditions, hard to setup without race simulation

---

## Agent Output Contract

Derived from analysis of a real HCM project (kept private). Applied as general standard across all projects using this agent pipeline.

### Doc Folder Structure

```
docs/
├── prd/{module}/            ← Requirement Gatherer — PRD pure (what/why)
│   ├── index.md               executive summary, personas, workflow map, NFR
│   └── {workflow}.md          actors, decision tree, business rules, wireframes
│                               NOT: Go code, SQL, endpoint request/response shapes
│
├── fr/{module}/             ← FR Writer — solution spec (AC + API contract)
│   ├── index.md               epic breakdown + ticket stubs
│   └── {workflow}.md          structured AC (condition → expected) + API response code table
│
├── architecture/            ← Architect — 3 modes
│   ├── domains.md             domain map, boundaries, interaction patterns
│   ├── {module}/
│   │   ├── design.md          Mode 1 output: strategic solution design
│   │   └── api-spec.md        Mode 2 output: API contracts, error codes, idempotency
│   └── adr/
│       └── {NNN}-{title}.md   individual ADRs
│
├── test-scenarios/          ← Test Explorer output
│   └── tester-{domain}-{date}.md
│
├── night-builds/            ← Night Builder output (plan + report per session)
│   └── {date}-{topic}-{plan|report}.md
│
└── discovery/               ← Requirement Gatherer research (append-only)
    └── {date}-{topic}.md
```

### Agent Ownership

See `AGENT_WORKFLOW.md` §Agent Contract Table — canonical mapping of reads/produces/consumers per agent. Do not duplicate here; update the workflow doc instead.

### Key Rules

1. `docs/prd/` — PRD only. No implementation detail (no code snippets, no SQL, no endpoint contract shapes). Decision tree and business rules YES. API request/response shape NO — that belongs in `docs/fr/`.
2. `docs/fr/{workflow}.md` must contain two mandatory sections: `## Acceptance Criteria` (condition → expected format) and `## API Response Codes` (table: code, HTTP, trigger, endpoint). Test Explorer depends on both.
3. `docs/architecture/` is split across modes: `design.md` (Mode 1) holds strategic design — domain boundaries, integration patterns, ADRs. `api-spec.md` (Mode 2) holds technical contract — endpoints, request/response shape, error codes, idempotency map, field-level constraints.
4. Test Explorer never greps code for response codes. If `docs/fr/` missing → flag gap, note incomplete, continue with Layer 1 only.
5. Night Builder and Architect are the only agents that touch code baseline.

### Example Migration Notes

- `docs/prd/{module}/00-architecture.md` should move to `docs/architecture/{module}/design.md`
- Existing workflow PRDs (e.g. `{workflow}-flow.md`) containing endpoint contracts — these should be extracted to `docs/fr/{module}/{workflow}-flow.md`
- `docs/ops/testing/e2e-test-plan.md` stays — it's env setup / operational. Test Explorer writes to `docs/test-scenarios/` separately.
