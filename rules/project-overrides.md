# Project Overrides — Template

> **This is a template, not a live rule.** It shows how a project layers its own
> deltas on top of the global rules in this repo (`git-workflow`, `testing`,
> `security`, `audit`, …). Copy it into a project's `.claude/rules/project-overrides.md`
> and fill the deltas. Global rules apply unless overridden here.

The pattern: keep the global rules generic and stable; capture every project-specific
divergence in ONE override file so a reader knows exactly where the project bends the
defaults. Absorb small per-language style guides here rather than scattering them.

---

## Language / Style (example — Go)

Capture the project's hard style choices so reviewers and agents converge:

1. **File size** — typical range, absolute max (e.g. 200–400 lines typical, 800 max)
2. **Function size** — under N lines
3. **Error handling** — always wrap: `fmt.Errorf("doing X: %w", err)`
4. **Context** — first parameter where applicable
5. **Interfaces** — define where consumed, not where implemented
6. **Repository pattern** — all DB access through interfaces
7. **Immutability** — prefer returning new structs over mutating
8. **Naming** — `snake_case` files, `camelCase` vars, `PascalCase` exports
9. **Constructors** — `New<Type>(deps) *Type`
10. **Config** — struct-based, loaded from env, validated at startup
11. **Logging** — structured logging with request id

---

## Testing (deltas on global `testing.md`)

- **Integration tests** — name the project's critical paths that MUST hit a real DB.
- **Coverage minimum** — restate the enforced number if the project differs from the
  global default.

---

## Security (deltas on global `security.md`)

- **JWT** — restate the project's exact token lifetimes + signing algorithm (symmetric
  vs asymmetric) so nobody guesses.
- **Auth context key** — name the exact context key the middleware sets (a wrong key →
  empty scope → queries return 0 rows; this class of bug is silent and expensive).
- **Domain-specific integrity** — anti-cheat / fraud / continuity checks unique to the
  project.

---

## Agent Trigger Heuristic (example)

When deciding whether to use a pipeline agent vs. edit directly:

| Scenario | Approach |
|----------|----------|
| New feature — no FR exists yet | Lean Mode: write code → land FR + contract block in same/next commit; `/spec <module>` for non-trivial features; ADR for non-obvious decisions. Heavy pipeline is on-demand, not mandatory. |
| Enhancement / bugfix — FR exists | Edit directly + update the contract block in the same PR |
| Docs drift detected | Advisory check on money/critical paths; `drift-triager` on demand; `fr-writer` only if the FR needs a substantial rewrite |
| New page / new sidebar link | Direct edit + `ux-consistency.md` Rule 1 checklist |
| DB migration | Direct edit + follow `migration-discipline.md` Rules 1–6 |
