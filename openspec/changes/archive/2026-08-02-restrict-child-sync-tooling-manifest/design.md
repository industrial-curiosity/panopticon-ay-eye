# Child Sync Tooling Manifest Design

## Context

Bootstrap already defines the child-safe module subset, but sync ignores it and
copies all `panopticon/` files. The two operations therefore have incompatible
module boundaries. A child-local manifest would also become stale, so the
instance must remain authoritative for each sync run.

## Goals / Non-Goals

**Goals:**

- Establish one instance-owned, child-safe tooling manifest.
- Fetch it on every sync run before selecting preview or write targets.
- Preserve existing child files outside the managed manifest.

**Non-Goals:**

- Remove previously copied CI-only files from children.
- Change child-owned files, provider configuration, or CI runtime imports.

## Decisions

The manifest will live in a dedicated template module. Bootstrap imports it
when vendoring local tooling; sync downloads that module from the selected
instance ref and executes it only in an isolated in-memory namespace to obtain
the manifest. Sync will filter the remote tree by exact manifest paths and
will retain its existing additive/overwrite behavior, never deleting an
out-of-manifest child file.

## Risks / Trade-offs

- [A local module is omitted from the manifest] → Bootstrap and sync manifest
  regression tests fail before release.
- [A child has a stale local manifest] → Sync ignores it and fetches the
  trusted instance source before every selection.

## Migration Plan

1. Add the instance-owned manifest and route bootstrap and sync through it.
2. Verify filtering, preview, and write behavior with unit tests.
3. Sync the template normally; existing unmanaged child files remain intact.

## Open Questions

None.
