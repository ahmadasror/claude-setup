# Claude Code Setup

Personal Claude Code configuration: custom agents, global rules, skills, and the
agent + cross-repo workflows that drive them.

## Structure

```
agents/                 # Custom subagent definitions (14)
skills/                 # Slash-command skills (e.g. /diskusi)
rules/                  # Global rules applied to all projects (13)
scripts/                # Reusable scripts (e.g. rebuild-handoff-index.py)
settings.json           # Global Claude Code settings
AGENT_WORKFLOW.md       # Agent pipeline — Lean Mode first, full spine as reference
CROSS_REPO_HANDOFF.md   # Multi-repo handoff workflow (provider ↔ consumer inbox)
```

> **Start here:** `AGENT_WORKFLOW.md` § *SDD Lean Mode* is the operative practice.
> The heavy multi-layer spine + 8-agent pipeline below it is **reference / opt-in**,
> not a mandatory gate. `CROSS_REPO_HANDOFF.md` is the live workflow for coordinating
> work across several repos owned by one operator.

## Install

```bash
git clone git@github.com:ahmadasror/claude-setup.git
cd claude-setup

mkdir -p ~/.claude/agents ~/.claude/rules ~/.claude/skills

cp agents/*.md ~/.claude/agents/
cp rules/*.md  ~/.claude/rules/
cp -r skills/* ~/.claude/skills/      # folder-per-skill (each has a SKILL.md)

# Review settings.json before copying — in particular
# "skipDangerousModePermissionPrompt" defaults to false here.
cp settings.json ~/.claude/settings.json
```

### Sync direction

One-way: edits happen in `~/.claude/` (and in per-project `.claude/`), then sync to
this repo. Repo is the mirror, not the source.

```bash
cp ~/.claude/agents/*.md agents/
cp -r ~/.claude/skills/*  skills/
git diff   # review before commit
```

## Operative practice — SDD Lean Mode

The mandatory process for a non-trivial feature is **three artifacts that pay rent**,
not an 8-agent pipeline:

1. **FR + machine-readable contract block** (`rules/fr-contract-block.md`)
2. **ADR** for any non-obvious decision
3. **Green test results**

Code-first is fine — land the FR + contract block in the same commit (or the immediate
follow-up). Drift is **advisory** on critical paths, not a blocking gate. The pipeline
agents below are **on-demand**, invoked when a specific feature warrants a stage. Full
detail + the retired layers: `AGENT_WORKFLOW.md` § *SDD Lean Mode*.

## Agents

### On-demand pipeline

| Agent | Purpose | Model |
|---|---|---|
| requirement-gatherer | Product strategy & workflow discovery → PRD | opus |
| product-digger | Domain-knowledge curator → `docs/product-knowledge/` (the reference layer other agents read) | opus |
| architect | Solution architect — solution-design (`design.md`) + conformity | opus |
| api-writer | API technical-spec author → `api-spec.md` + API Contract Block (split out of architect Mode 2) | opus |
| fr-writer | Functional requirements from PRD + architecture (+ FR Contract Block + UI Selectors) | opus |
| tester-explorer | Test scenarios — 3 phases progressive (+ Test Scenario Contract Block + Tier annotation) | opus |
| test-builder | Generate + run Playwright specs (TC ID + tier tag) | sonnet |
| night-builder | Autonomous unattended builder — code + unit tests | sonnet |
| drift-triager | Classifies drift detector output (FR-ahead / Code-ahead / Real-mismatch / Waiver × P0/P1/P2) | sonnet |

### Supporting

| Agent | Purpose | Model |
|---|---|---|
| architect-financial | Financial-grade architecture (audit, idempotency, immutable ledger) | opus |
| planner | Implementation strategy planning | opus |
| presenter | HTML slide decks (management-level) — see `STYLE_GUIDE.md` | opus |
| security-reviewer | Security vulnerability review | sonnet |

### Retired (kept as reference)

| Agent | Status |
|---|---|
| pimpro | **Retired** in Lean Mode — a standing per-completion supervisor was overhead. Status is derived on-demand instead. |

## Skills

Slash-command skills invoked as `/<name>` in any project. Global by default — drop a
`SKILL.md` in `<project>/.claude/skills/<name>/` to override per-project.

| Skill | Purpose |
|---|---|
| `/diskusi` | Memandu diskusi PRD topik-per-topik dengan tracker pemahaman terpisah (`docs/prd/{module}/comprehension.md`). Satu topik per sesi, 2–3 pertanyaan konfirmasi, progress persist antar sesi. Invocation: `/diskusi prd <module>`, `/diskusi prd <module> <topik>`, `/diskusi status <module>`. |

## Rules

**Core (generic):**
- **audit.md** — explicit audit for CUD operations
- **git-workflow.md** — conventional commits, branch naming
- **security.md** — no hardcoded secrets, parameterized queries
- **testing.md** — TDD workflow, table-driven tests
- **migration-discipline.md** — schema migrations as net deltas; `ON CONFLICT` parse-time matching; dry-run before promoting
- **wait-patterns.md** — reliable service-readiness waits (HTTP probe, healthcheck) vs. the `docker logs --tail` sliding-window trap
- **scope-discipline.md** — IN vs OUT scope; if a change has a named existing consumer, the consumer update is part of the task
- **batch-query-over-loop.md** — kill N+1: one batched `IN (:ids)` query → Map/Set → loop in-memory
- **cross-repo-handoff.md** — provider/consumer roles for the markdown-inbox handoff protocol
- **fr-contract-block.md** — FR Contract Block + code-comment marker grammar (for projects that ship a drift detector)

**Domain-shaped patterns (labeled examples):**
- **approval-routing.md** — maker-checker SoD; resolve approver at creation time; two resolver patterns
- **ux-consistency.md** — discoverability, permission-gated nav, scope-based sections, confirm-dialog policy
- **project-overrides.md** — *template* for layering project-specific deltas on the global rules

## Cross-repo workflow

`CROSS_REPO_HANDOFF.md` + `scripts/rebuild-handoff-index.py` + `rules/cross-repo-handoff.md`
implement a lean, operator-driven protocol for coordinating wire-contract work across
several repos (backend ↔ mobile ↔ assistant service): a consumer raises a markdown
handoff in its `docs/handoffs/<provider>/` inbox; the provider verifies, appends a
resolution, flips status, regenerates the index. The README index is generated, never
hand-edited.

## Docs

- **AGENT_WORKFLOW.md** — Lean Mode (operative) + the full traceability spine and
  cross-agent contracts (UI Selectors, FR Contract Block, Test Scenario Contract Block,
  Test Result Ratchet, PRD Contract Block, Test Tiering) as reference.
- **CROSS_REPO_HANDOFF.md** — the multi-repo handoff workflow.
- **PROPOSAL_FOR_OTHER_PROJECTS.md** — adoption guide for the heavy spine + drift
  detector (opt-in; start from Lean Mode and add layers only as they pay rent).
- **STYLE_GUIDE.md** — visual design system for the `presenter` agent's slide decks.
- **CLAUDE.md** — project-level instructions and agent output contract.
- **samples/** — end-to-end sample outputs per agent, using a fictional `orders` module.

## Companion Repos

- **[ahmadasror/drift-detector](https://github.com/ahmadasror/drift-detector)** —
  canonical drift detector binary (Go, MIT) shipping the contract schemas + extractors
  referenced by `rules/fr-contract-block.md` + `AGENT_WORKFLOW.md`. In Lean Mode it runs
  **advisory** on critical paths, not as a blocking gate.

## License

MIT — see `LICENSE`.
