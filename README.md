# Claude Code Setup

Personal Claude Code configuration: custom agents, global rules, hooks, and settings.

## Structure

```
agents/       # Custom subagent definitions (11 agents)
rules/        # Global rules applied to all projects
hooks/        # Shell scripts triggered by Claude Code hooks
settings.json # Global Claude Code settings
```

## Install

```bash
# Clone
git clone git@github.com:ahmadasror/claude-setup.git

# Symlink or copy to ~/.claude/
cp -r agents/* ~/.claude/agents/
cp -r rules/* ~/.claude/rules/
cp -r hooks/* ~/.claude/hooks/
cp settings.json ~/.claude/settings.json
```

## Agents

| Agent | Purpose |
|---|---|
| architect | Enterprise architecture review |
| architect-corebanking | Core banking architecture (OJK/BI compliance) |
| architect-financial | Financial-grade architecture (audit, idempotency) |
| doc-tidier | Documentation auditor & restructurer |
| fr-writer | Functional requirements from PRD |
| go-reviewer | Go code quality review |
| night-builder | Autonomous unattended builder |
| planner | Implementation strategy planning |
| requirement-gatherer | Product strategy & workflow discovery |
| security-reviewer | Security vulnerability review |
| tdd-guide | Test-driven development workflow |

## Rules

- **audit.md** - Explicit audit for CUD operations
- **git-workflow.md** - Conventional commits, branch naming
- **security.md** - No hardcoded secrets, parameterized queries
- **testing.md** - TDD workflow, table-driven tests
