# Complete Rollout Status and Legacy Tooling Guidance

## Why

The rollout plan has no durable status ledger or accurately labelled current
baseline, making it difficult to distinguish completed local work from
unstarted and operationally proven work. Child repositories can also retain
CI-only or unknown `panopticon/` files from the earlier broad-sync behavior
without receiving a warning or a reviewed migration path.

## What Changes

- Add a maintained rollout-plan status ledger and a clearly labelled current
  baseline; record that a true pre-change baseline was not captured.
- Make child sync and advisory tooling-currency checks identify files outside
  the instance-owned local-tooling manifest without deleting them.
- Classify candidates as instance files excluded from the child manifest or as
  child-only unknown files, and give maintainers a reviewed-removal procedure.
- Document the warning and migration process in the organization setup guide
  and child `PANOPTICON.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: Child sync must warn about unmanaged tooling files and
  preserve them for reviewed removal.
- `tooling-currency`: The advisory check must identify tooling files outside
  the local-tooling manifest and distinguish instance-excluded from child-only
  candidates.

## Impact

This changes `panopticon/sync.py`, `panopticon/tooling_currency.py`, their
tests, rollout and onboarding documentation, and the two capability
specifications. It adds no dependencies and does not delete or overwrite an
unmanaged child file.
