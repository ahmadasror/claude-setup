# UX Consistency Rules

> **Domain-shaped pattern (example rule).** Drawn from a multi-persona web app
> (employee / manager / admin / finance), but the discoverability, permission-gating,
> and confirm-dialog principles generalize to any role-based UI. Adapt selectors and
> store helpers to your stack.

Rules for keeping the UI predictable so a user never has to "discover" a feature by
URL-guessing. Codified after an incident where a permission was seeded for weeks, the
pages existed and worked, but **no sidebar link** existed — the user could only reach
the feature by typing the URL. User feedback verbatim: *"biar ga dikit-dikit ketemu ini
itu kagetan"* (stop surprising me by making me stumble onto things).

## Core Principle

**Every user-facing permission has a discoverable UI surface.** If a role has a
`*_own` permission for a feature, that role's sidebar (or a workflow-natural entry
point) must lead to the feature. A seeded permission with no entry point is a
half-finished feature.

The inverse also holds: every sidebar link must be gated on a real permission, not a
role bucket alone. Role buckets drift; permission-gated links survive role redefinition.

## Rules

### 1. New `*_own` permission for end users → sidebar entry in the same PR

When seeding a permission named like `<domain>.<verb>_own` that any end-user role
grants, add the matching Self-Service sidebar link in the same PR — gated on the
specific permission, with a stable `data-testid` (E2E specs assert presence/absence by
that selector).

### 2. New page route → entry-point check before merge

Before merging a PR that adds a new page, answer: **who is the target user?**, **from
which existing surface should they land here?**, **is that surface wired in this PR?**
If not, the page is orphan — fix in the same PR or document explicitly why deferral is
OK (feature flag off, design pending). Orphan pages erode trust.

### 3. Use permission gates, not role buckets, on individual links

```
✅ v-if="can('hr.contract_alerts')"   — survives role redefinition
❌ v-if="isHR"                          — breaks when a role gains/loses permissions
```

Section-level gates (`canSeeHR`) are OK as a coarse filter, but the individual `v-if`
on each link must check the specific permission.

### 4. Section headers render only when at least one link is visible

Use a `*AnyVisible` aggregate computed so an empty section header never renders. An
empty header signals "something should be here for me" with no payload — worse than no
section at all.

### 5. A registry is the source-of-truth inventory

Keep a per-persona expected-menu doc. Before declaring a feature complete, verify the
registry matches the rendered sidebar for each affected persona. It feeds E2E sidebar
tests, the new-feature PR checklist, and drift reviews.

### 6. Section grouping — scope determines section, not role

Sections cluster by **scope of the data shown**, not by who's logged in:

- **Operational / admin section** — cross-entity / configurational scope (list-all,
  monitor, configure across many subjects).
- **Self-Service section** — first-person scope (pages that ONLY show the logged-in
  user's own data).
- **Workflow / approvals section** — approver-side inboxes (data spans submitters).

A user who wears two hats sees BOTH sections; the features don't mix because the
sections are separate. **Never put a cross-entity aggregate in Self-Service**, and
**never put a first-person "my" page in the admin section** — the section header is the
"which hat am I wearing" cue.

### 7. Workflow entry points are part of the feature, not "next steps"

If the feature is a multi-step workflow (submit → approve → confirm → consume), each
role's entry point lands in the same PR: submitter (start button/link), approver
(inbox shows the pending item), reviewer (search/filter), downstream consumer (the
page that reads the output). Shipping the submit page without wiring the approver inbox
is a half-feature.

### 8. Hide approve/reject when an external workflow is in flight

When an approval is backed by an external workflow engine, decisions route through that
engine's endpoint, not a direct-mode endpoint. Gate the direct Approve/Reject buttons
on `!workflow_instance_id` (direct mode only); hide them when a workflow is in flight.
A stale button calling a removed endpoint yields a 404 → `JSON.parse` error → cryptic
browser alert.

### 9. File upload UI: single inline dropzone, not init-then-upload split

Prefer a **single inline dropzone** on the page where the user lands. Avoid "modal asks
metadata → create empty shell → redirect → upload there" — users click "New" expecting
an upload prompt and instead get a metadata form with no file picker. When a shell-first
pattern is genuinely needed, put the dropzone INLINE in the same modal.

### 10. Template / format guidance lives in external docs, not in-app

Don't render a "Download template" button inside the upload UI. Format spec belongs in
the FR doc and the team SOP. In-app templates bloat the bundle, age out of sync with
backend validators, and create "is this still the right template?" doubt.

### 11. State-mutating actions REQUIRE a confirm dialog

Every button that changes non-trivial state must go through a confirm step first. No
"click → immediate action".

| Action | Variant | Message must mention |
|---|---|---|
| Submit for review | `warning` | row count + total + "locked until approved/rejected" |
| Approve / commit | `warning` or inline form-dialog with summary | row count + total + "cannot undo" |
| Reject (needs notes) | inline form-dialog (needs textarea) | min-char rule for notes |
| Cancel / delete | `danger` | whether terminal + whether data is lost |
| Lock / unlock | `warning` / `danger` | scope of impact (who is affected) |
| Bulk delete N rows | `danger` | N + a few example names + "permanent" |

Does NOT need confirm: read-only/navigation/filter, saving a form (the form *is* the
commitment), pagination/sort/refresh, UI toggles, opening a "+ New" form dialog.

Use a global `useConfirm()` composable for yes/no decisions; use an inline form-dialog
when the action needs input (notes, reason, file) or a data summary (table/list).
Variant guidance: `info` low-risk reversible · `warning` significant but recoverable ·
`danger` destructive/terminal. Never use native `window.confirm()`; never make a
confirm un-cancellable via Esc / backdrop-click.

## Anti-patterns

- ❌ Seeding a permission and not surfacing it in the sidebar
- ❌ A new page with no link from anywhere
- ❌ Role-gated `v-if` on a sidebar link instead of permission-gated
- ❌ A section header that renders for a user who can't see any link inside it
- ❌ "Discoverability is Phase 2" — that means the user has to ask "where is X?", which
  is exactly the failure mode this rule prevents
- ❌ A cross-entity aggregate page in Self-Service, or a first-person `/my/*` page in
  the admin section
- ❌ `@click="deleteRecord(id)"` with no confirm — the most common misclick
- ❌ A generic "Are you sure?" that doesn't name the specific consequence
