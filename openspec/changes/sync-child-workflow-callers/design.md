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
- Reuse the existing caller-text generator so bootstrap and sync cannot drift.

**Non-Goals:**

- Synchronizing arbitrary child-owned workflows or workflow files.
- Changing the instance provider configuration or child secrets/variables.
- Automatically committing or pushing child changes.

## Decisions

- Fetch the instance org configuration at the child workflow ref and resolve
  its trusted provider contract before generating callers. The local child
  config identifies the instance/ref but does not duplicate mutable provider
  settings.
- Treat the fixed `CALLER_WORKFLOWS` set as the complete managed surface.
  Sync creates missing callers and overwrites content-different callers, exactly
  like bootstrap.
- Compare generated caller bytes with local files for dry-run reporting. This
  covers callers without requiring a separate remote workflow-tree protocol.
- Fail loudly on inaccessible or invalid instance configuration rather than
  writing guessed callers. This matches bootstrap's provider-config behavior.

## Risks / Trade-offs

- [An instance changes provider configuration] → Sync intentionally rewrites
  the PR caller to the newly configured provider; child maintainers review the
  generated diff before committing.
- [A child customized a managed caller] → Sync intentionally overwrites it;
  caller workflows are managed resources and custom workflows remain outside
  the fixed filenames.
- [Remote configuration cannot be read] → Sync makes no workflow changes and
  reports the configuration failure with recovery context.

## Migration Plan

1. Release the sync update through the instance repository.
2. Existing children run `python3 -m panopticon.sync` and commit the resulting
   reviewable diff; missing callers, including resource sync, are created.
3. `--check-updates` remains available to preview the exact managed resources.
