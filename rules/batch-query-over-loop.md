# Batch-Query-Over-Loop Rule

Rules for avoiding N+1 database access: never issue one query per element inside a
loop/stream when a single batched `IN (:ids)` query gets the same data.

## Core Principle

A loop that calls `repo.findByX(item.getId())` / `repo.countByX(id)` /
`repo.existsByX(id)` once per iteration is an **N+1**: 1 query to get the list + N
queries inside the loop. Replace it with **one** batched query keyed by the collection
of IDs, then index the result into a `Map` / `Set` and loop **in-memory**.

The win is wall-clock + DB round-trips: 16 rows × 1 COUNT = 16 queries becomes 1
`GROUP BY`; 300 items × 1 find = 300 queries becomes 1 `WHERE id IN (...)`. Round-trip
latency dominates on a list/render or bulk path — that's where this matters most.

## When it applies

Any of these shapes, in Java or Go:

```java
for (X x : items)            { repo.findByY(x.getId()); }      // ❌ N+1
items.forEach(x ->             repo.countByY(x.getId()));        // ❌ N+1
items.stream().map(x ->        repo.existsByY(x.getId()))...     // ❌ N+1
```
```go
for _, x := range items      { db.Get(ctx, x.ID) }              // ❌ N+1
```

The tell: a repository / DB call whose **argument varies per iteration** by a single
id. That id-set is exactly what an `IN`-query consumes.

## The canonical fix

### 1. Add a batched repository method (derived query, name it `…In`)

Spring Data derives `IN` queries from method names — no `@Query` needed for simple cases:

```java
List<Result> findByParentIdAndChildIdIn(UUID parentId, List<UUID> childIds);
List<Result> findByParentIdInAndChildId(List<UUID> parentIds, UUID childId);
List<Catalog>  findByCodeIn(Collection<String> codes);
```

For an aggregate count per key, write the `GROUP BY` explicitly and return
`List<Object[]>` of `[key, count]`:

```java
@Query("SELECT r.parentId, COUNT(r) FROM Result r WHERE r.parentId IN :ids GROUP BY r.parentId")
List<Object[]> countByParentIdIn(@Param("ids") List<UUID> ids);
```

Always Javadoc **which N+1 it replaces** — the next reader needs to know it's not
redundant with the per-row finder that still exists for single-row call sites.

### 2. Refactor the call site: fetch once → Map/Set → loop in-memory

```java
List<UUID> ids = items.stream().map(X::getId).toList();
if (ids.isEmpty()) return ...;                       // short-circuit: no query at all
Map<UUID, Foo> byId = repo.findByIdIn(ids).stream()
        .collect(Collectors.toMap(Foo::getId, f -> f, (a, b) -> a));   // (a,b)->a: tolerate dups
for (X x : items) {
    Foo f = byId.get(x.getId());                     // in-memory, no query
}
```

When the loop only needs *existence*, collect a `Set<UUID>` and `contains()`. When
index-alignment matters (two parallel lists), keep looping the original ordered
collection and look up each by key.

## Hard caveats (do NOT skip)

### A. Never `JOIN FETCH` a collection to "also batch the children"

If the loop body reads a lazy `@OneToMany`, batching the **parent** fetch is correct,
but resist the urge to `LEFT JOIN FETCH r.children` in the batch query. Fetch-joining a
collection across many query roots **bag-duplicates** the parent rows (a classic
Hibernate-bag inflation: a sum computed ×N). Leave children lazy; the parent N+1 is
gone and that's the win. If child-loading is itself hot, batch it separately
(`findChildrenByParentIdIn` + group in memory), never via fetch-join.

### B. Behaviour-preserving on find-or-create write loops

For a find-or-**create** loop: prefetch existing rows into a **mutable** `Map`, pass
the looked-up row (or null) into the worker, and **update the map** with whatever the
worker creates/saves — otherwise a duplicate key in the same batch re-creates instead
of updating, silently diverging from the prior re-read-each-time semantics. Make the
worker `return` the saved entity so the caller can keep the map current.

### C. Preserve counts / flags exactly

When replacing `findX().orElseGet(() -> save(...))` (save-if-absent) with a pre-batched
`Set.contains()` guard, keep any side counters (`skipped++`, `flagged++`) firing on the
same condition as before — batch the *lookup*, not the *accounting*.

### D. Stored aggregates stay stored

Don't "simplify" a materialized column (a stored snapshot total) into a live `SUM()`
just because you're touching the query. Those are snapshots (often immutability-guarded);
only the live per-render count belongs in the batched query.

## Test pattern: stub the batch method with `thenAnswer`

Unit tests that stubbed the per-row finder break when you switch to the batch method.
Back the stub with a map + `thenAnswer` so each test keeps seeding by key:

```java
private final Map<UUID, Foo> byKey = new HashMap<>();

@BeforeEach
void setUp() {
    lenient().when(repo.findByParentIdInAndChildId(any(), any())).thenAnswer(inv -> {
        List<UUID> ids = inv.getArgument(0);
        return ids.stream().map(byKey::get).filter(Objects::nonNull).toList();
    });
}
// each test: byKey.put(parentId, result);
```

If the production code keys the batch result by `getParentId()`, the test fixtures
**must set `parentId` on each result** (a builder that drops it keys on null). Add a
`verify(repo, never()).findByParentIdAndChildId(any(), any())` to lock in that the
per-row path is dead.

## When NOT to bother

- **Fixed, tiny, constant id-set** (e.g. 3 hardcoded keys) — 3 queries is already
  optimal; a batch adds no value. Comment that it's intentional.
- **Genuinely single-row call sites** — keep the per-row finder; the batched method is
  additive, not a replacement.
