# Migration Discipline Rules

Rules for writing schema migrations (Flyway, golang-migrate, Alembic, any tool)
without breaking predecessors and without expensive rebuild loops.

## Core Principle

A migration is a **net delta on top of every prior migration**, not a fresh
design. Read what's already there, then design the smallest change that lands the
new requirement without breaking existing callers — including hardcoded SQL inside
locked migration files (e.g. `ON CONFLICT (cols)` clauses you cannot edit).

## Rules

### 1. Audit predecessors BEFORE writing the new migration

Before opening the new migration file, scan **all prior migrations** for things the
schema change must preserve:

- Every `ON CONFLICT (cols)` and `ON CONFLICT ON CONSTRAINT name` clause — the
  matching unique/exclusion must remain in the schema (or be replaced with one
  PostgreSQL can infer at parse time).
- Every `UNIQUE` / `PRIMARY KEY` / `CHECK` constraint — note the name, columns, and
  any `WHERE` predicate. Anything that depends on the constraint name (like
  `ON CONFLICT ON CONSTRAINT`) breaks if the name changes.
- Every `FOREIGN KEY` referencing a column you plan to alter — the cascade
  behaviour, deferrable status, ON DELETE rule.
- Every locked-format migration (Flyway Java migrations, Alembic ops with
  checksums) — these cannot be edited; you must work around them.

If a predecessor uses bare `ON CONFLICT (a, b, c)` and you're tempted to replace the
matching unique with a partial unique `(a, b, c) WHERE x IS NULL`, **do not** — bare
ON CONFLICT only matches non-partial uniques at parse time (see Rule 2).

Output of this audit: a checklist of "things we must preserve" pinned at the top of
the new migration as a SQL comment.

### 2. PostgreSQL `ON CONFLICT` validates at PARSE time, not runtime

Even on an empty table, a query containing `ON CONFLICT (cols) DO ...` fails
immediately with `SQL State 42P10 — there is no unique or exclusion constraint
matching the ON CONFLICT specification` if no matching constraint exists.

Implication: **dropping a unique that any locked migration's ON CONFLICT depends on
breaks every reset / re-apply of that migration**, even when the data wouldn't
actually conflict.

| Form | Matches |
|---|---|
| `ON CONFLICT (a, b, c) DO ...` | non-partial unique on exactly `(a, b, c)` |
| `ON CONFLICT (a, b, c) WHERE p DO ...` | partial unique on `(a, b, c)` whose predicate implies `p` |
| `ON CONFLICT ON CONSTRAINT name DO ...` | the named constraint, partial or not |
| `ON CONFLICT DO NOTHING` (no target) | matches any unique on the row's columns |

If you must support both a "strict N-tuple unique" (for legacy ON CONFLICT) and an
"(N+1)-tuple unique with a new discriminator column" (for the new feature), **keep
both** — the strict tuple as a partial unique excluding the new type, plus the wider
unique covering everything. They coexist as long as no row falls in both predicates
simultaneously.

### 3. Encrypted columns are not byte-stable across writes

Columns wrapped by an AES-GCM (or any IV-randomised) ORM-level converter re-encrypt
with a fresh IV on every `save()`, even when the plaintext is unchanged. The DB
column changes after every UPDATE that touches the row.

Consequence:

- Migrations that backfill encrypted columns must use the entity / converter path
  (or a service-layer encrypt helper) — not `UPDATE table SET col = '<plaintext>'`.
- Tests that snapshot "before" state for an immutability assertion must read
  PLAINTEXT (via HTTP / repo / decrypted query), not raw SQL.
- "Should be unchanged" data-quality checks at runtime must compare plaintext, not
  the DB column.

### 4. Raw dry-run BEFORE promoting to a migration file

Each "edit migration → delete history → rebuild image → restart container → wait for
boot → check" cycle costs minutes. Five iterations is real waiting time.

Faster loop: write the SQL in a scratch buffer, paste it into the running DB, watch
it succeed or fail, iterate. Only when the SQL works against the live DB do you
commit it to a `V<N>__name.sql` file.

```bash
# Dry-run the SQL against the live dev DB
docker exec <postgres-container> psql -U <user> -d <db> <<'SQL'
ALTER TABLE foo ADD COLUMN ...;
CREATE UNIQUE INDEX IF NOT EXISTS ...;
SQL
# If it works, copy into V<N>__feature.sql and commit
```

For idempotency-sensitive migrations, run the dry-run twice — second pass must be a
no-op.

When a Flyway migration has been applied with one body and you've since edited the
body (checksum changes), Flyway refuses to start with `Migration checksum mismatch`.
Recovery (dev only): `DELETE FROM <schema>.flyway_schema_history WHERE version='<N>'`
then restart. Never amend an already-applied migration in production.

### 5. Test ordering is part of the migration contract

If your migration changes state-machine semantics or constraint shape, existing test
specs **may** be ordering-sensitive. State-mutating tests (lock, void, terminate) put
a row into a state where subsequent re-run/re-correction calls fail with a different
error than the validation case expects.

When changing a constraint or a service-layer guard, sweep the relevant serial test
blocks and verify the order matches the new contract:

1. Read-only / SETUP first
2. Validation / rejections (state-independent)
3. Happy-path non-mutating
4. Happy-path mutating (creates the state others depend on)
5. Business rules (read post-mutation state)
6. Audit-chain queries (read audit trail of #4–#5)
7. Terminal state — lock / confirm — **absolute last**

If a test's expected error code changed because of an ordering issue, fix the order,
not the assertion.

### 6. Cross-schema and cross-service constraints

Migrations affecting tables read from a different service (e.g. one service reading
another's tables via cross-schema SQL) must check that service has `GRANT SELECT` on
the affected schema. A new column is invisible to the reading role until the grant is
refreshed. After any DROP+restore, re-apply schema-level GRANTs — `pg_restore
--no-privileges` strips them.

When an integration depends on a cross-language internal HTTP API, encode the response
shape in a contract — particularly date formats. Go's `time.Time` JSON encoder
produces RFC-3339 (`2024-06-01T00:00:00Z`); Java's `LocalDate.parse` rejects that.
Use a two-step parse (`OffsetDateTime.parse(...).toLocalDate()`) on the consumer side.

## Migration Header Template

```sql
-- V<N> — <short title>.
--
-- Predecessor audit (Rule 1):
--   - V<NN>: ON CONFLICT (col_a, col_b) — preserved
--   - V<NN>: UNIQUE INDEX uq_xyz — replaced with partial below
--   - V<NN>: CHECK status IN (...) — extended to add 'CORRECTED'
--
-- Behaviour change:
--   - <one paragraph explaining what callers will observe>
--
-- Idempotency: <Yes / No / via DELETE FROM history>
-- Rollback: <how to undo, or "forward-only">
```

If the audit table is empty, the migration is touching virgin tables and probably
doesn't need this rule — but the section stays for the next reader.
