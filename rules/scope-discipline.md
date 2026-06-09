# Scope Discipline Rules

Rules for deciding what is IN scope vs OUT of scope on a single change. Codified
after a concrete miss: a backend endpoint shipped clean, the spec doc unilaterally
declared "UI is OUT OF SCOPE", and the existing frontend form sat one ~30-line edit
away from picking up the new field. Avoidable.

## Core Principle

Scope follows **what the change touches in the running system**, not what feels neat
in a PR. If a backend endpoint change has an existing frontend caller within the same
repo, the frontend update is part of the task by default. Carving the FE off into a
"follow-up" without explicit user agreement is unilateral scope cutting.

## Rules

### 1. Before declaring "UI out of scope", check for existing callers

Before writing "UI is out of scope" / "frontend is a follow-up" / "FE wiring
deferred", grep for existing pages that call the affected endpoint:

```bash
grep -rn "<endpoint-path>\|<HandlerName>" frontend/pages frontend/components frontend/composables
```

If a hit exists, the FE change is **part of the task**, not a follow-up. The cost of
the FE edit is usually < 5% of the backend work for an additive field (one form, one
payload key, optional dropdown options).

### 2. "Follow-up" is acceptable only when…

- **Greenfield UI** — no existing page renders this concept. Building the page IS a
  separate feature.
- **Large UI** — new route, new permission gate, multiple components, new visual
  design. Reasonable to land BE first and stage FE in a second PR.
- **User explicitly agrees** — get the agreement in the conversation, not buried as a
  unilateral paragraph in a spec doc.
- **Permission gate not yet defined** — the FE change can't ship without a permission
  decision the user hasn't made.

When NONE of those apply, wire it.

### 3. Backend-only is the wrong default in autonomous mode

When the user gives an autonomous-mode brief — "continue until clean test", "commit
and push if green", "carry on till done" — they expect a working feature, not a
half-feature waiting on FE work. Backend-only with the FE buried as "next steps"
violates that contract.

If you genuinely can't decide whether the FE is in scope, **ask once** before
pre-committing to a cut. Don't bury the decision in a spec document.

### 4. Apply the same rule to other adjacent surfaces

The pattern: if the new thing has a *named existing consumer* in the repo, the
consumer update is part of the task.

- **Backend endpoint change** + **existing frontend caller** → FE update in same PR
- **Schema change** + **existing seed file referencing the table** → seed update in same PR
- **New field** + **existing audit pipeline** → audit metadata stamp in same PR
- **New permission** + **existing role assignment** → role grant in same PR
- **New enum value** + **existing test fixtures** → fixture update in same PR
- **Workflow definition edit** + **existing contract block referencing it** → block update in same PR

### 5. Sync rules go in the spec

When a feature requires two-place edits to stay coherent (e.g. a FE allow-list map
mirroring a BE allow-list map), document the sync rule explicitly in the spec's UI
section so the next reader (or agent) knows the constraint:

> Sync rule: adding a subtype = edit BOTH `<feMap>` (frontend) AND `<beAllowlist>`
> (backend) in the same PR. There is intentionally no shared schema file — the count
> is small enough that two-place duplication is cheaper than a codegen pipeline.

### 6. Cross-cutting capabilities use the shared service — no per-domain re-implementation

When a capability is **cross-cutting** (the same need recurs across business domains),
build it ONCE as a shared, domain-agnostic service and route every domain through it.
Do **not** add a new per-domain variant of an existing cross-cutting capability — that
is sprawl, and it compounds (every future domain adds another copy).

Concrete shape of the anti-pattern: each domain that needed a file upload (selfie,
correction, attachment) had grown its **own** upload endpoint. The Nth domain would
have been the Nth bespoke copy. Resolution: ONE shared attachment service,
domain-agnostic (uploader-scoped reads, generic claim + retention — no
`switch owner_domain`), integrated in two lines per domain.

**The governance rule:**
- **New cross-cutting need → the shared service. No new per-domain copy.** A new
  domain adds itself to an `owner_domain` allowlist (one line) and calls the shared
  API.
- The same test applies to any cross-cutting capability (notification fan-out, audit
  emit, file export, signed-PDF generation): if a second domain needs it, it belongs
  in a shared service, not copy-pasted.
- **Anti-sprawl design check:** a shared service that still requires per-domain code
  on its hot path (a `switch domain { ... }`, a per-domain ACL function, a per-domain
  prune branch) has only *relocated* the sprawl. Make the shared service
  domain-agnostic; push domain-specific authz to the domain's own detail endpoint.
- Existing per-domain implementations may stay (additive) but **converge over time**.

## Anti-patterns

- ❌ Writing "UI is OUT OF SCOPE — follow-up" without grepping for existing callers
- ❌ Listing the FE work in a "Next steps" section of the closing report — that's not
  handoff, that's a backlog
- ❌ Splitting BE and FE into two PRs when the FE delta is < 50 lines and depends on
  no new design decision
- ❌ Pre-deciding scope in the spec document instead of in the conversation
- ❌ Adding a new per-domain variant of a cross-cutting capability instead of routing
  through the shared service (Rule 6)
- ❌ A "shared" service that still needs per-domain code on its hot path — that
  relocates sprawl, doesn't remove it

## What this rule is NOT

- NOT "always ship FE with BE." Greenfield UI, permission gates, design dependencies
  all justify deferral.
- NOT "ignore PR size discipline." Reviewable PR size still applies — in a solo repo
  the threshold is "self-reviewable in one sitting", which 50-line FE diffs are.
- NOT a critique of backend-first staging when there's a real reason (feature-flag
  gate, async rollout). The rule is against UNDOCUMENTED unilateral scope cuts.
