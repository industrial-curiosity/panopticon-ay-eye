# Shared child resource sync design

## Context

`python3 -m panopticon.sync` already refreshes an initialized child repository's
Panopticon skills and vendored tooling from the instance repository. It is a
local, write-in-place command; organizations lack a shared Actions path that
can run the same update and present the resulting diff for review.

## Goals / Non-Goals

**Goals:**

- Give every newly bootstrapped child a stable manual resource-sync caller.
- Keep synchronization logic template-owned and repairable on the next run.
- Create or update a reviewable child-repository PR only when managed resources
  actually differ.
- Keep the instance-read token separate from the child-repository write token.

**Non-Goals:**

- Automatically merge or directly push managed resource changes to a default
  branch.
- Re-run initialization, generate documentation, or update indexes.
- Support scheduled synchronization in the initial release.

## Decisions

### Use a fixed child caller and a template-owned reusable workflow

Bootstrap writes a small `panopticon-resource-sync.yml` caller. It invokes a
fixed template reusable workflow at `@main`, following the existing
template-to-instance sync pattern. The shared implementation therefore evolves
without every child receiving a new full workflow.

### Reuse the existing local sync behavior

The shared workflow checks out the child default branch and runs
`python3 -m panopticon.sync`. It updates the same managed skills and vendored
tooling as the local command, preserving one authoritative resource-selection
implementation.

### Review updates through a durable PR

When synchronization changes files, the workflow pushes a deterministic
bot-owned branch and creates or updates one PR against the child default branch.
When no managed file changes, it exits successfully without a branch or PR.

### Separate read and write credentials and restrict execution

The child caller maps `PANOPTICON_INSTANCE_TOKEN` only to the reusable
workflow's instance-read secret. The child workflow's `GITHUB_TOKEN` writes the
update branch and PR with minimal `contents` and `pull-requests` permissions.
The shared workflow rejects runs whose checked-out ref is not the child default
branch before using the instance credential, preventing a manually dispatched
untrusted branch from receiving it.

## Risks / Trade-offs

- A child default branch may restrict bot branch pushes or PR creation → report
  the failed permission and leave no misleading success message.
- A stale caller file cannot receive new triggers or permissions automatically
  → keep it minimal; shared logic still fixes behavior on its next invocation.
- An existing bot PR can contain maintainer edits → update only the managed
  branch and clearly identify it as automation-owned.

## Migration Plan

New bootstraps receive the caller automatically. Existing children can add the
small caller from the instance/template once; subsequent behavior updates come
from the shared workflow. Rollback removes the caller or disables its manual
workflow without altering managed resources.

## Open Questions

None.
