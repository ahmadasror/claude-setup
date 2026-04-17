# Claude Setup — Global Agent Config

This repo mirrors the agent definitions, hooks, and rules from `~/.claude/`.

## Sync Convention

Sync direction depends on the assignment:

- **`~/.claude/` → repo**: after editing agents/rules locally, push to repo to persist
- **repo → `~/.claude/`**: after pulling updates from another machine or collaborator

```bash
# ~/.claude → repo
cp ~/.claude/agents/*.md agents/
git add -p && git commit -m "chore: sync agents from ~/.claude"

# repo → ~/.claude
cp agents/*.md ~/.claude/agents/
```

Always check which side is newer before syncing.

---

## Agent Design Decisions

### tester-explorer

**Status**: Active — being iterated

**Purpose**: QA intelligence agent. Reads domain docs, extracts state machines and workflows, maps seed data needs, then generates test scenarios. Output drives both manual and automated test execution.

**Position in agent flow**:
```
requirement-gatherer → PRD
architect            → Architecture doc
fr-writer            → Epics + Ticket stubs with AC
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

Derived from analysis of txhcs project (`~/code/txhcs`). Applied as general standard across all projects using this agent pipeline.

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
├── architecture/            ← Architect — design level only
│   ├── domains.md             domain map, boundaries, interaction patterns
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

| Agent | Reads from | Writes to | Touches code |
|---|---|---|---|
| requirement-gatherer | User input, discovery | `docs/prd/`, `docs/discovery/` | NO |
| fr-writer | `docs/prd/` | `docs/fr/` | NO |
| architect | `docs/prd/`, `docs/fr/` | `docs/architecture/` | Read-only (patterns) |
| tester-explorer | `docs/prd/`, `docs/fr/` | `docs/test-scenarios/` | NO |
| night-builder | `docs/fr/`, `docs/architecture/` | Code, `docs/night-builds/` | YES |

### Key Rules

1. `docs/prd/` — PRD only. No implementation detail (no code snippets, no SQL, no endpoint contract shapes). Decision tree and business rules YES. API request/response shape NO — that belongs in `docs/fr/`.
2. `docs/fr/{workflow}.md` must contain two mandatory sections: `## Acceptance Criteria` (condition → expected format) and `## API Response Codes` (table: code, HTTP, trigger, endpoint). Test Explorer depends on both.
3. `docs/architecture/` is design level — domain boundaries, interaction patterns, ADRs. NOT: specific field names, specific response codes, validation rules (those live in `docs/fr/`).
4. Test Explorer never greps code for response codes. If `docs/fr/` missing → flag gap, note incomplete, continue with Layer 1 only.
5. Night Builder and Architect are the only agents that touch code baseline.

### txhcs Migration Notes

- `docs/prd/platform-admin/00-architecture.md` should move to `docs/architecture/platform/design.md`
- Existing workflow PRDs (e.g. `leave-request-flow.md`) contain endpoint contracts — these should be extracted to `docs/fr/leave/leave-request-flow.md`
- `docs/ops/testing/e2e-test-plan.md` stays — it's env setup / operational. Test Explorer writes to `docs/test-scenarios/` separately.
