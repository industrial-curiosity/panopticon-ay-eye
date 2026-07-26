## Why

Child repositories initialized before a new managed caller workflow exists stay
permanently incomplete: `python3 -m panopticon.sync` refreshes skills and local
tooling but cannot add or update workflow callers. Re-running bootstrap is an
unnecessary and confusing recovery path for routine managed-resource updates.

## What Changes

- Extend local child resource sync to detect, preview, create, and refresh all
  managed Panopticon caller workflows.
- Generate workflow callers from the child configuration and the instance's
  current provider contract so refreshed callers remain configuration-correct.
- Preserve the dry-run guarantee of `--check-updates` and report workflow
  changes alongside skills and tooling.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `tooling-currency`: Local sync refreshes managed child workflow callers in
  addition to skills and vendored tooling.
- `repo-initialization`: Bootstrap and later resource sync share the managed
  caller-workflow contract.

## Impact

- Affects `panopticon/sync.py`, caller-workflow generation/config loading, and
  sync tests.
- Lets previously bootstrapped children acquire
  `.github/workflows/panopticon-resource-sync.yml` without rerunning bootstrap.
