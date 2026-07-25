# Fix vendored provider tooling and initialization reporting

## Why

Fresh child repositories cannot run the vendored documentation and finalization
commands because `config.py` imports `providers.py`, but bootstrap and sync do
not vendor that module. When initialization finds problems, its output is also
terminal-only and mixes ownership and remedies, leaving users without a clear,
durable account of what needs attention.

## What Changes

- Vendor `panopticon/providers.py` with the other local child-repository
  tooling during both bootstrap and template sync.
- Make finalization always write a concise initialization report, including
  unsuccessful runs.
- Organize every reported item by owner — template/tooling, child repository,
  or organization configuration — and give a direct next action and location.
- Update user-facing guidance and tests for the vendored dependency and report
  contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: Child tooling must include its runtime import
  dependencies, and finalization must leave an actionable, durable report.

## Impact

Affected code includes `panopticon/bootstrap.py`, `panopticon/sync.py`, and
`panopticon/init_repo.py`, along with their tests and initialization guidance.
The change adds a child-repository report artifact but introduces no external
service or dependency.
