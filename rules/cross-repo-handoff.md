# Cross-Repo Handoff Rule

How a **consumer** repo asks a **provider** repo to confirm or extend a wire
contract, and how the provider replies — without either side editing the other's
source. This is a lean, operator-driven, markdown-inbox protocol for coordinating
work across repository boundaries when one human operator (+ AI agents) owns
several repos. For anything bigger (≥2 diverging consumer teams) reach for
contract-testing (Pact) instead — until then this is the right weight.

> This rule is the **live** path. A heavier message-bus sibling (a Slack/agent
> daemon that relays structured `Action: handoff|done|ack` messages) is the
> parked alternative — re-activate that only when handoff volume outgrows a
> human reading an inbox folder.

## When this applies

A change that crosses a repo boundary and needs the other side to act: a consumer
needs a provider to confirm a DTO, add an endpoint, or provision infra. Both repos
are reachable by one operator (commonly checked out side by side on one host).

## Core invariants

1. **Strict repo boundary.** The consumer never edits/builds/tests the provider's
   repo, and vice versa. The **only** file the provider writes into the consumer's
   tree is the handoff file inside the consumer's shared inbox
   (`<consumer>/docs/handoffs/<provider>/`).
2. **Append-only; the README index is GENERATED — do NOT hand-edit it.** Never edit
   the request prose. The provider replies by appending one `## <PROVIDER> resolution`
   section and flipping the `Status:` line **at the top of the handoff file** — that
   `Status:` header is the single source of truth. The inbox README's table is
   auto-generated between `<!-- HANDOFF-INDEX:START -->` / `<!-- HANDOFF-INDEX:END -->`
   markers by `scripts/rebuild-handoff-index.py` (run it, or let a pre-commit hook
   run it, before committing). Hand-editing the index row re-introduces the
   bilateral README race this protocol replaced.
3. **Read off-disk; git for the trail.** When both repos sit on one host, read the
   inbox directly. Commits exist to pin a stable SHA, not as the delivery channel.
4. **One source of truth = the consumer's inbox.** The provider keeps no mirror
   index; it back-links via a commit footer (invariant 7) instead.

## The lifecycle

`open → acknowledged → in-progress → answered → accepted → closed`

| Who sets | Transition |
|---|---|
| consumer | raises `open` |
| provider | `acknowledged → in-progress → answered` |
| consumer | `accepted` (wire bound) `→ closed` |

**Immutability:** once a handoff reaches `accepted`, its request body is **frozen**.
A later contract change is a **new** handoff that *supersedes* the old one with an
explicit link — never a rewrite of the accepted request. This is what makes the
inbox a trustworthy trail rather than a mutable scratchpad. No backward transitions
(`answered → open`).

## The resolution section (provider side)

Append `## <PROVIDER> resolution` as the last section. It MUST carry:

- **Verification line** — confirm every `file:line` the consumer cited actually
  matches the provider repo as-read. The consumer localizes the ask into *your*
  repo's coordinates; verify before answering.
- **The confirmed contract** — exact DTO field names / envelope, or a pointer to a
  spec. Tables, not prose, for field lists.
- **Decisions, separated from the request** — when the operator makes a call (e.g.
  "single gateway host", "defer endpoint X"), record the *what + why* as a
  lightweight ADR (`docs/architecture/adr/`) and **link it** from the resolution.
  The handoff captures the *request*; the ADR captures the *decision*. Never bury a
  durable decision in handoff prose only — that loses the rationale and the ETA.
- **SHA pin** — if the answer shipped code, pin the provider commit SHA. If a build
  is deferred, say so explicitly with an ETA (or "no SHA yet") — never leave a
  deferred item without a stated next step.

Then flip `Status:` (file header) to `answered`.

## Handoff file template

```markdown
# Handoff: <slug>

Status: open
Type: feature | bug | contract-confirm | infra
Raised: YYYY-MM-DD
From: <consumer> → <provider>

## What I need
<concrete ask — endpoint, DTO confirm, infra. Cite provider file:line where known.>

## Why
<the consumer-side feature this unblocks>

## Proposed contract (consumer's guess — provider confirms or corrects)
<tables for request/response shape>

<!-- provider appends "## <PROVIDER> resolution" below and flips Status -->
```

## Commit conventions

- **Provider → consumer back-link.** The provider's implementing commit carries a
  footer: `Resolves: <consumer>!handoff-<slug>`. This is the only back-reference
  the provider keeps — no mirror index needed.
- **Inbox commit lives in the consumer repo.** The provider may *write + commit* the
  resolution into the consumer's inbox (it is the shared box), but the **push** of
  the consumer repo is the consumer side's call. The provider keeps its own repo SHA
  pushed (that carries the trail).

## Git-sync discipline

The inbox working tree may lag `origin`. Before editing a handoff:

```bash
git -C <consumer-repo> fetch -q origin
# materialize just the inbox without disturbing unrelated local edits:
git -C <consumer-repo> checkout origin/main -- docs/handoffs/<provider>/
```

Edit, then commit only `docs/handoffs/<provider>/`. If the consumer tree diverges,
the consumer side linearizes (rebase) — the provider does not force it.

## Both sides codify their role

Each repo keeps its own copy of this rule labelled by role:
- consumer repo → `cross-repo-handoff.md` (raiser) — raise, then flip to `accepted`/`closed`.
- provider repo → `cross-repo-handoff.md` (responder) — verify, append resolution, flip to `answered`.

The inbox README is the canonical bilateral protocol both honor.

## Anti-patterns

- ❌ Editing the request prose instead of appending a resolution.
- ❌ Rewriting an `accepted` handoff in place — open a superseding one.
- ❌ Recording a decision only in handoff prose (no ADR, no rationale, no ETA).
- ❌ A diff that touches more than the `Status` line + placeholder on the reply.
- ❌ Hand-editing the generated README index table.
- ❌ Reaching for Pact / a schema-validated index / a message-bus daemon at low
  volume (a handful of handoffs/week) — that is the parked heavier sibling's weight,
  not this. Add a machine-readable index only past ~50 active handoffs.

## See also

- `CROSS_REPO_HANDOFF.md` (repo root) — the full protocol writeup + `scripts/rebuild-handoff-index.py`.
- `rules/fr-contract-block.md` — the in-repo machine-readable contract surface; the
  cross-repo edge could later grow an OpenAPI file at the gateway boundary as its analog.
