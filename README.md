# Claude Code Setup

Personal Claude Code configuration: custom agents, global rules, and settings.

## Structure

```
agents/       # Custom subagent definitions (12 agents — 8 pipeline + 4 supporting)
rules/        # Global rules applied to all projects (6 rules)
settings.json # Global Claude Code settings
```

> Single source of truth for pipeline order, inputs/outputs, and contracts: `AGENT_WORKFLOW.md`.
>
> Adopting this pipeline on a new GitHub project: `PROPOSAL_FOR_OTHER_PROJECTS.md`.

## Install

### Prerequisites

- Claude Code CLI installed
- `~/.claude/` directory exists (created on first Claude Code run)

### Copy to Claude Code profile

```bash
git clone git@github.com:ahmadasror/claude-setup.git
cd claude-setup

mkdir -p ~/.claude/agents ~/.claude/rules

cp agents/*.md ~/.claude/agents/
cp rules/*.md  ~/.claude/rules/

# Review settings.json before copying — in particular
# "skipDangerousModePermissionPrompt" defaults to false here.
cp settings.json ~/.claude/settings.json
```

### Sync direction

One-way: edits happen in `~/.claude/`, then sync to this repo. Repo is the mirror, not the source.

```bash
# After editing ~/.claude/agents/*.md locally
cp ~/.claude/agents/*.md agents/
git diff   # review before commit
```

## Agents

### Pipeline (8)

| Agent | Purpose | Model |
|---|---|---|
| requirement-gatherer | Product strategy & workflow discovery → PRD (+ optional PRD Contract Block L1) | opus |
| architect | Solution architect — 3 modes: solution-design (design.md) · technical-spec (api-spec.md) · conformity | opus |
| fr-writer | Functional requirements from PRD + Architecture (+ FR Contract Block L2 + UI Selectors) | opus |
| tester-explorer | Test scenarios — 3 phases progressive (+ Test Scenario Contract Block L4 + Tier annotation) | opus |
| test-builder | Generate + run Playwright specs (TC ID substring + tier tag mandatory; feeds L5 ratchet) | sonnet |
| night-builder | Autonomous unattended builder — code + unit tests + L3 code-comment markers | sonnet |
| pimpro | Pipeline status aggregator — Recent Activity (event-driven default) + Drift Status (full sweep on user trigger) | sonnet |
| drift-triager | Reads drift detector output, classifies entries (FR-ahead / Code-ahead / Real-mismatch / Waiver) × P0/P1/P2 + per-link sub-class | sonnet |

### Supporting (4)

| Agent | Purpose | Model |
|---|---|---|
| architect-financial | Financial-grade architecture (audit, idempotency) | opus |
| planner | Implementation strategy planning | opus |
| presenter | HTML slide decks (management-level) | opus |
| security-reviewer | Security vulnerability review | sonnet |

See `AGENT_WORKFLOW.md` for execution order, inputs/outputs, cross-agent contracts (UI Selectors, FR Contract Block, Code-Comment Marker, Test Scenario Contract Block, Test Result Ratchet, PRD Contract Block, Test Tiering).

## Rules

- **audit.md** - Explicit audit for CUD operations
- **git-workflow.md** - Conventional commits, branch naming
- **security.md** - No hardcoded secrets, parameterized queries
- **testing.md** - TDD workflow, table-driven tests
- **fr-contract-block.md** - FR Contract Block (L2) + Code-Comment FR-Marker (L3) — mandatory for projects that ship a drift detector
- **wait-patterns.md** - Reliable service-readiness wait patterns (HTTP probe, healthcheck) and anti-patterns (`docker logs --tail` sliding window)

## Docs

- **AGENT_WORKFLOW.md** - Pipeline execution order, input/output per agent, and cross-agent contracts (5-link traceability spine, UI Selectors, FR Contract Block, Code-Comment Marker, Test Scenario Contract Block, Test Result Ratchet, PRD Contract Block, Test Tiering, helper-script pattern).
- **PROPOSAL_FOR_OTHER_PROJECTS.md** - Adoption guide: how to bootstrap this pipeline + drift detector on a new GitHub project (Phases 0-5).
- **STYLE_GUIDE.md** - Visual design system for HTML slide decks consumed by the `presenter` agent.
- **CLAUDE.md** - Project-level instructions and agent output contract.
- **samples/** - End-to-end sample outputs per agent (PRD → Architecture → FR → Test Scenarios → Playwright specs → Night build report → Status dashboard → Drift triage), using a fictional `orders` module as the running example.

## Companion Repos

- **[ahmadasror/drift-detector](https://github.com/ahmadasror/drift-detector)** — canonical drift detector binary. Single Go binary, MIT, ships all 5 schemas + extractors + examples for the FR Contract Block, Code-Comment Marker, Test Scenario Contract Block, Test Result Ratchet, and PRD Contract Block patterns referenced by `agents/drift-triager.md` + `rules/fr-contract-block.md` + `AGENT_WORKFLOW.md`. Adopt via `go install github.com/ahmadasror/drift-detector/cmd/drift-detector@latest` or fork to extend.

## License

MIT — see `LICENSE`.
