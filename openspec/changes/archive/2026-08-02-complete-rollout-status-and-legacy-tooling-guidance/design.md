# Rollout Status and Legacy Tooling Guidance Design

## Context

The instance-owned manifest now limits child sync to child-safe modules, but
children created under the previous broad-sync behavior may still contain
CI-only source files. They are preserved silently. The rollout plan also lacks
a durable record of which steps are implemented, locally verified, or proven
in a real child environment.

## Goals / Non-Goals

**Goals:**

- Give maintainers advisory, actionable classifications for unmanaged child
  Python modules.
- Provide a reviewed-removal migration procedure without automatically removing
  files.
- Add an execution-status ledger and honest current-baseline record to the
  rollout plan.

**Non-Goals:**

- Introduce a manifest schema version or a second source of truth.
- Delete, move, or overwrite an unmanaged child file.
- Treat child configuration, indexes, `.gitignore`, or bytecode as tooling
  migration candidates.
- Claim that a pre-change baseline exists when it was not captured.

## Decisions

### Scan only unmanaged Python source paths

Sync and tooling-currency will compare child `panopticon/**/*.py` paths against
the remote manifest. A path that also exists in the instance tree but is absent
from the manifest is an instance-excluded candidate; any other path is a
child-only unknown candidate. This scopes warnings to the files that broad
sync could have installed, without conflating local state with tooling.

### Warn in both local sync and PR advisory checks

Local sync reports candidates during preview and apply so a maintainer sees
them while refreshing. Tooling-currency emits its existing non-blocking GitHub
Actions warnings on pull requests. Neither path changes the sync exit status or
modifies candidates.

### Make removal a reviewed maintainer action

The setup guide and child guide will instruct maintainers to preview, inspect
each candidate's ownership and imports, remove only reviewed unwanted files,
then run tests and commit the removal separately. This preserves child-owned
extensions and prevents automated cleanup from deleting code.

### Keep rollout evidence in the plan

The plan will contain a compact status ledger with an OpenSpec change reference
and one of `unstarted`, `implemented`, `locally verified`, or operationally
proven for every numbered step. Its baseline record will state that the true
pre-change baseline is unavailable and give the current verification command
and result date instead.

## Risks / Trade-offs

- [A child-owned module receives an advisory warning] → Warnings classify it as
  unknown, never delete it, and require maintainer review.
- [A CI-only module is intentionally retained for local experimentation] → The
  maintainer can retain it; the warning is advisory.
- [The ledger becomes stale] → Each subsequent rollout-plan change updates the
  affected status row and evidence link.

## Migration Plan

1. Add classification helpers and regression coverage for both warning paths.
2. Publish the template change so children receive the refreshed sync module.
3. Maintainers run `python3 -m panopticon.sync --check-updates`, review each
   candidate, and remove only files they explicitly approve.
4. Run the child test suite and commit approved removals separately from the
   tooling refresh.

## Open Questions

None.
