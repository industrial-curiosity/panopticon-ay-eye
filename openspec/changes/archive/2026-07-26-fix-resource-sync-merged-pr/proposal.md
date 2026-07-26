# Fix resource-sync merged PR reuse

## Why

The shared child resource-sync workflow can locate a historical merged pull
request by its automation branch and report it as updated after pushing new
resources. A merged or closed pull request is not an active review surface, so
the next changed sync must open a new reviewable pull request.

## What Changes

- Define the reusable resource-sync pull request as an open pull request only.
- Require a new pull request after the prior automation pull request is merged
  or closed.
- Cover the lifecycle distinction with a workflow regression test.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tooling-currency`: Define the automation pull request lifecycle for the
  shared child resource synchronization workflow.

## Impact

- `.github/workflows/shared-child-resource-sync.yml` selects an open pull
  request before deciding whether to update or create one.
- `tests/test_resource_sync_workflow.py` verifies the state-constrained lookup.
- Child repository maintainers receive a new resource-sync pull request after
  merging or closing the prior one.
