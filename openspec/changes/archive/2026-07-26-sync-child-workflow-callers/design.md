## Context

Bootstrap writes four thin child workflow callers from the instance provider
configuration. Local sync currently downloads only skills and vendored Python
modules, so it cannot repair or add a managed caller introduced after a child
was first bootstrapped.

## Goals / Non-Goals

**Goals:**

- Make local sync reconcile every managed child caller workflow with the
  instance's current configuration.
- Keep `--check-updates` read-only and make its workflow findings explicit.
- Deliver every module required by local sync as part of one managed directory
  reconciliation, without copying caller metadata into multiple modules.

**Non-Goals:**

- Synchronizing arbitrary child-owned workflows or workflow files.
- Changing the instance provider configuration or child secrets/variables.
- Automatically committing or pushing child changes.

## Decisions

- Reconcile managed directories from the instance tree into a staging area,
  then apply their updates only after the complete source set is available.
- Treat `panopticon/`, the selected skill location, and Panopticon-managed
  workflow callers as directory-backed managed resources. Sync only creates or
  overwrites managed paths; it never deletes a child path. Preserve explicitly
  protected paths, including the child initialization config and child-owned
  workflow files, rather than maintaining a module allowlist.
- Keep the caller workflow list and renderer in one shared module. Bootstrap
  and sync import that module after the managed directory is available.
- Make `--check-updates` report directory-derived additions, updates, and
  protected files without writing any path.

## Risks / Trade-offs

- [A child has a protected file under a managed directory] → Preserve it and
  report that protection rather than overwriting it; sync never deletes files.
- [A prior sync has an incomplete module set] → A one-time recovery replaces
  the local sync entrypoint; future syncs stage the complete managed directory
  before using newly added modules.
- [Remote configuration cannot be read] → Sync makes no workflow changes and
  reports the configuration failure with recovery context.

## Migration Plan

1. Release the sync update through the instance repository.
2. Existing children run `python3 -m panopticon.sync` and commit the resulting
   reviewable diff; missing callers, including resource sync, are created.
3. `--check-updates` remains available to preview the exact managed resources.
