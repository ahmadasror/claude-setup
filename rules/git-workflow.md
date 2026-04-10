# Git Workflow Rules

1. **Conventional commits** — `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
2. **Branch naming** — `feat/feature-name`, `fix/bug-name`, `refactor/scope`
3. **PR scope** — One concern per PR, keep it reviewable (< 400 lines diff)
4. **Never force push** to `main` or `develop`
5. **Squash merge** to main for clean history
6. **CI must pass** before merge — lint + test + security scan
