# Approval Routing — Canonical Pattern

> **Domain-shaped pattern (example rule).** This encodes lessons from an HR/finance
> approval system, but the SoD invariants and the two resolver patterns generalize to
> any maker-checker workflow. Adapt table/column names to your schema.

Rules for setting an approval request's `approver_id` at creation time. Codified after
a debugging marathon where three different resolvers drifted across services and a
placeholder-then-fix pattern bit us in three distinct ways within an hour.

## Core invariants

1. **Never fall back to the requester / uploader as approver.** That's a
   maker-equals-checker SoD violation; an inbox filter `approver_id = me` will route
   the approval to the requester's own inbox.
2. **Resolve at creation time, not after-the-fact.** Setting a placeholder and
   expecting a later workflow callback to fix it doesn't work — there is usually no
   such callback.
3. **The role column on the user is the source of truth.** If a `user_roles` JOIN
   table exists but is unused / empty, any resolver that queries it returns empty and
   triggers a fallback. Confirm which one your app actually populates.

## Two canonical patterns

### Pattern A — entity-scoped (manager-as-approver)

Use when the approval is about ONE subject entity and its direct owner/manager is the
natural approver: a leave request, an individual expense, a record change.

```
resolveApprover returns user_id of:
  1. entity.manager_id (FK to users.id) when set
  2. first active <admin-role> in the org via users.role
  3. "" — caller MUST decide fail-vs-fallback policy
```

Keep every service-local implementation of this chain **byte-for-byte aligned**. Drift
between them is a bug.

### Pattern B — org-scoped role-based

Use when the approval is NOT tied to a specific entity, OR the approver role is fixed by
workflow definition rather than reporting chain: a batch approval, a period close, a
bulk operation.

```go
approverID, err := approvalRepo.FindFirstActiveUserByRole(ctx, orgID, "<role>")
if err != nil { return fmt.Errorf("resolving approver: %w", err) }
if approverID == "" {
    return apperror.New(409, "NO_APPROVER_AVAILABLE",
        "No active <role> user in this org — assign the role to at least one user")
}
```

**Always read the role column, not an unused JOIN table.**

## Anti-patterns

- ❌ `ApproverID: actorID, // placeholder — workflow assigns actual approver` — if there
  is no "workflow assigns" code path, this lands the approval in the maker's own inbox.
- ❌ Fallback to the current user's id when no manager / no admin found. Re-creates the
  maker-vs-checker problem.
- ❌ Querying an empty `user_roles` JOIN instead of the populated role column.
- ❌ Per-service resolver implementations that diverge — keep them aligned.

## Strict vs lenient fallback

When the role resolver returns empty, callers choose:

| Approval type | Policy when no approver found | Rationale |
|---|---|---|
| Batch / bulk | **strict** — return 409 `NO_APPROVER_AVAILABLE` | Maker is already known; self-approve = SoD violation |
| Individual (manager chain) | admin-role fallback OK | The subject can't be expected to know their manager wasn't set |
| Record correction | admin-role fallback OK | Same reason |
| Money flow (period close) | strict | Must have an explicit org-level signer |

When in doubt, prefer strict. A 409 with a clear error code beats a silent SoD bypass.

## How to add a new approval type

1. Decide Pattern A (entity-scoped) or Pattern B (org-scoped role-based).
2. Pattern A: implement a service-local `resolveApprover` matching the existing ones
   exactly (manager_id → admin-role via role column → "").
3. Pattern B: call the canonical role resolver directly. Pick the strict policy unless
   there's a clear product reason for lenient.
4. NEVER set `ApproverID: actorID` as a placeholder. If you can't resolve at create
   time, the resolver itself is buggy — fix that.
