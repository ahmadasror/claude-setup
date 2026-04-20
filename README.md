# Claude Code Setup

Personal Claude Code configuration: custom agents, global rules, hooks, and settings.

## Structure

```
agents/       # Custom subagent definitions (11 agents — 7 pipeline + 4 supporting)
rules/        # Global rules applied to all projects
hooks/        # Shell scripts triggered by Claude Code hooks
settings.json # Global Claude Code settings
```

> Single source of truth for pipeline order, inputs/outputs, and contracts: `AGENT_WORKFLOW.md`.

## Install

### Prerequisites

- Claude Code CLI installed
- `jq` (required by `hooks/update-confluence.sh`) — `brew install jq` / `apt install jq`
- `~/.claude/` directory exists (created on first Claude Code run)

### Copy to Claude Code profile

```bash
git clone git@github.com:ahmadasror/claude-setup.git
cd claude-setup

mkdir -p ~/.claude/agents ~/.claude/rules ~/.claude/hooks

cp agents/*.md ~/.claude/agents/
cp rules/*.md  ~/.claude/rules/
cp hooks/*.sh  ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh

# Review settings.json before copying — in particular
# "skipDangerousModePermissionPrompt" defaults to false here.
cp settings.json ~/.claude/settings.json
```

### Hook configuration (optional)

- **`sync-planka-to-claude-md.sh`** — fires after Planka card updates. Requires project to have `CLAUDE.md` at its root; otherwise hook is a no-op.
- **`update-confluence.sh`** — fires after `ExitPlanMode`. Requires project-level `.claude/confluence.json` with fields `{url, space, section}`; absent → no-op.

### Sync direction

One-way: edits happen in `~/.claude/`, then sync to this repo. Repo is the mirror, not the source.

```bash
# After editing ~/.claude/agents/*.md locally
cp ~/.claude/agents/*.md agents/
git diff   # review before commit
```

## Agents

### Pipeline (7)

| Agent | Purpose | Model |
|---|---|---|
| requirement-gatherer | Product strategy & workflow discovery → PRD | opus |
| architect | Enterprise architecture review → design.md + ADR | opus |
| fr-writer | Functional requirements from PRD + Architecture | opus |
| tester-explorer | Test scenarios (3-phase progressive) | opus |
| test-builder | Generate + run Playwright specs, write test report | opus |
| night-builder | Autonomous unattended builder (code + unit tests) | opus |
| pimpro | Pipeline status aggregator / dashboard | sonnet |

### Supporting (4)

| Agent | Purpose | Model |
|---|---|---|
| architect-financial | Financial-grade architecture (audit, idempotency) | opus |
| planner | Implementation strategy planning | opus |
| presenter | HTML slide decks (management-level) | opus |
| security-reviewer | Security vulnerability review | sonnet |

See `AGENT_WORKFLOW.md` for execution order, inputs/outputs, cross-agent contracts (UI Selectors).

## Rules

- **audit.md** - Explicit audit for CUD operations
- **git-workflow.md** - Conventional commits, branch naming
- **security.md** - No hardcoded secrets, parameterized queries
- **testing.md** - TDD workflow, table-driven tests

## Docs

- **AGENT_WORKFLOW.md** - Pipeline execution order, input/output per agent, and cross-agent contracts (UI Selectors, helper-script pattern).
- **STYLE_GUIDE.md** - Visual design system for HTML slide decks consumed by the `presenter` agent.
- **CLAUDE.md** - Project-level instructions and agent output contract.
- **samples/** - End-to-end sample outputs per agent (PRD → Architecture → FR → Test Scenarios → Playwright specs → Night build report → Status dashboard), using a fictional `orders` module as the running example.

## License

MIT — see `LICENSE`.
