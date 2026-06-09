# Cross-Repo Handoff Workflow

A lean, operator-driven protocol for coordinating work across repository boundaries
when **one operator (+ AI agents) owns several repos** — e.g. a backend, a mobile
app, and an AI/assistant service that all integrate over wire contracts.

It replaces ad-hoc "ping me on chat to add this endpoint" coordination with a
**markdown inbox** committed into the consumer repo: durable, greppable, and a clean
audit trail of who asked for what and how it was resolved. It is the **live** path; a
heavier Slack/agent message-bus daemon is the parked alternative for when volume
outgrows a human reading a folder.

> This doc is the full writeup. Each participating repo also keeps a short
> role-labelled `rules/cross-repo-handoff.md` (see `rules/cross-repo-handoff.md` here)
> so its own agents know how to raise vs. respond.

---

## The shape

```
consumer repo                              provider repo
─────────────                              ─────────────
docs/handoffs/<provider>/                  (no mirror — back-links via commit footer)
├── README.md          ← generated index
├── handoff-<date>-<slug>.md   ← request + appended resolution
└── done/              ← archived terminal handoffs (accepted/closed)
```

The consumer raises a handoff file in **its own** `docs/handoffs/<provider>/` inbox.
The provider reads it (off-disk when both repos sit on one host, or via git), verifies
the cited `file:line` claims against its own source, **appends** a resolution section,
flips the status, and regenerates the index. The provider's *only* write into the
consumer tree is that one handoff file.

A repo that is **both** a provider to some and a consumer of others hosts an inbox per
provider it depends on, and answers in the inboxes that name it as provider.

---

## Roles

| Role | Does | Never does |
|---|---|---|
| **Consumer** (raiser) | Raises the handoff, cites the wire need, confirms (`accepted`) once the wire is bound, pushes its own repo | Edits/builds/tests the provider repo |
| **Provider** (responder) | Verifies claims, appends `## <PROVIDER> resolution`, ships code in its own repo, pins SHA, flips to `answered` | Pushes the consumer repo (that's the raiser's call) |

---

## Lifecycle

`open → acknowledged → in-progress → answered → accepted → closed`

| Set by | Transition | Meaning |
|---|---|---|
| consumer | → `open` | request raised |
| provider | → `acknowledged` | seen, queued |
| provider | → `in-progress` | working it |
| provider | → `answered` | resolution appended; SHA pinned or ETA stated |
| consumer | → `accepted` | wire bound and verified on the consumer side |
| consumer | → `closed` | done; file archived to `done/` by the index script |

**Immutability:** once a handoff is `accepted`, its request body is frozen. A later
contract change is a **new, superseding** handoff with an explicit link — never an
in-place rewrite. No backward transitions.

---

## The handoff file

```markdown
# Handoff: <slug>

Status: open
Type: feature / new API surface
Raised: YYYY-MM-DD
From: <consumer> → <provider>

## What I need
<concrete ask. Cite provider file:line where you think it lives — the provider verifies.>

## Why
<the consumer feature this unblocks>

## Proposed contract (consumer's best guess — provider confirms or corrects)
| Field | Type | Notes |
|---|---|---|
| ... | ... | ... |

<!-- provider appends below and flips Status to `answered` -->
```

### The provider's resolution section (appended, last)

```markdown
## <PROVIDER> resolution

Status flipped: open → answered

**Verification.** Confirmed the cited paths against <provider> as-read:
- `path/to/file.go:NN` — matches / corrected to `path/to/other.go:MM`

**Confirmed contract.**
| Field | Type | Notes |
|---|---|---|
| ... | ... | ... |

**Decision.** <if the operator made a call, link the ADR: docs/architecture/adr/NNN-*.md>

**Shipped.** Provider SHA `<sha>` on `origin/main`. (Or: "no SHA yet — ETA <date>".)
```

---

## The generated index

`docs/handoffs/<provider>/README.md` carries an **auto-generated** table between
`<!-- HANDOFF-INDEX:START -->` / `<!-- HANDOFF-INDEX:END -->`. Do NOT hand-edit it —
the single source of truth is the `Status:` header inside each handoff file. Run
`scripts/rebuild-handoff-index.py` (included here) before committing; it:

1. scans `handoff-*.md`,
2. moves `accepted`/`closed` files into `done/` (the archive — not listed in README),
3. rewrites the table sorted newest-first.

Wire it as a pre-commit hook and a `--check` CI gate so the index can never drift from
the files. Configure the `INBOXES` list at the top of the script for your repo.

---

## Commit conventions

- **Provider → consumer back-link.** The provider's implementing commit carries a
  footer: `Resolves: <consumer>!handoff-<slug>`. That is the only back-reference the
  provider keeps — no mirror index.
- **Inbox commit lives in the consumer repo.** The provider may write + commit the
  resolution into the consumer's inbox, but the **push** of the consumer repo is the
  consumer's call. The provider keeps its own repo SHA pushed (that carries the trail).

## Git-sync discipline

The inbox working tree may lag `origin`. Before editing:

```bash
git -C <consumer-repo> fetch -q origin
git -C <consumer-repo> checkout origin/main -- docs/handoffs/<provider>/
```

Edit, then commit only `docs/handoffs/<provider>/`. If the consumer tree diverges, the
consumer linearizes (rebase) — the provider never force-pushes the consumer.

---

## Setting it up on a new estate

1. In each consumer repo, create `docs/handoffs/<provider>/README.md` with the marker
   block + a copy of the bilateral protocol header.
2. Drop `scripts/rebuild-handoff-index.py` (from this repo) into each repo; set
   `INBOXES`.
3. Install the pre-commit hook (run the script) + a `--check` CI step.
4. Add `rules/cross-repo-handoff.md` to each repo's `.claude/rules/`, labelled by the
   repo's role (raiser vs responder).
5. For an AI-agent loop, give the responder a recurring "scan inbox" task: `git fetch`,
   read open/acknowledged/in-progress handoffs, verify, append resolution, flip status.

## When NOT to use this

- A single repo — there's no boundary to coordinate across.
- ≥2 *diverging* consumer teams of the same provider — graduate to consumer-driven
  contract testing (Pact) or a published OpenAPI spec at the boundary.
- Very high volume (~50+ active handoffs) — add a machine-readable index; consider the
  parked message-bus daemon.

## See also

- `rules/cross-repo-handoff.md` — the per-repo role rule (raiser / responder).
- `scripts/rebuild-handoff-index.py` — the index generator.
- `AGENT_WORKFLOW.md` — the in-repo agent pipeline this coordinates between.
