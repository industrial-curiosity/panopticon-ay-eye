## Why

Child repositories initialized before a new managed caller workflow exists stay
permanently incomplete: `python3 -m panopticon.sync` refreshes skills and local
tooling but cannot add or update workflow callers. Re-running bootstrap is an
unnecessary and confusing recovery path for routine managed-resource updates.

## What Changes

- Reconcile complete managed resource directories so new Panopticon modules and
  callers arrive together rather than through an incomplete file allowlist.
- Preserve every existing child file; sync only creates or overwrites managed
  resources and never deletes paths.
- Preserve the dry-run guarantee of `--check-updates` and report workflow
  changes alongside skills and tooling.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `tooling-currency`: Local sync reconciles managed resource directories with
  explicit protected paths.
- `repo-initialization`: Bootstrap and later resource sync share complete
  managed resource directories.

## Impact

- Affects `panopticon/sync.py`, caller-workflow generation/config loading, and
  sync tests.
- Lets previously bootstrapped children acquire
  `.github/workflows/panopticon-resource-sync.yml` without rerunning bootstrap.
