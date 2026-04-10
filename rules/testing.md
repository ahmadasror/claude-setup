# Testing Rules

1. **TDD workflow** — RED → GREEN → IMPROVE for all new features
2. **Minimum 80% coverage** — Enforced in CI
3. **Table-driven tests** (Go) — Use `t.Run()` with descriptive names
4. **Test behavior, not implementation** — Tests should survive refactoring
5. **No shared mutable state** — Each test is independent
6. **Mock at boundaries** — Mock repositories/external services, not internal logic
7. **Integration tests** — Hit real database for critical paths
8. **Name pattern** — `Test<Function>_<Scenario>_<Expected>` (e.g., `TestCreateUser_DuplicateEmail_ReturnsConflict`)
