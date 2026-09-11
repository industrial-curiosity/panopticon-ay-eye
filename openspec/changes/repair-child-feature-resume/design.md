# Child Feature Resume Design

## Context

The feature receipt and helper are vendored into a child repository, but the
feature registry remains instance-owned. The generic feature-check CLI loads a
registry, so it cannot validate a child checkout. Finalization already reads a
receipt without the registry and invokes the installed helper.

## Goals / Non-Goals

**Goals:**

- Let initialization finish after the agent repairs an enabled feature in a
  child repository.
- Keep receipt validation and feature-helper execution deterministic.
- Preserve checkpoint retention for genuine unresolved feature findings.

**Non-Goals:**

- Vendoring the instance feature registry into child repositories.
- Changing instance or CI feature validation.
- Changing feature modes or checkpoint ordering.

## Decisions

Use `panopticon.init_repo` as the child-side revalidation boundary. It already
validates the local receipt and installed helper, including when no manifest is
present. The init skill and finalization report will direct agents to repair
through the installed feature skill and rerun finalization, rather than invoke
the instance-root CLI.

The alternative—copying the manifest into every child—would expand managed
child state solely to support a command whose existing finalization path is
already sufficient. The alternative of weakening `panopticon.features check`
would blur its instance-root contract and duplicate the receipt-only behavior.

## Risks / Trade-offs

- [Risk] A child receipt may be malformed. → `init_repo` retains its current
  controlled validation failure and blocks finalization.
- [Risk] The installed helper may be missing or invalid. → `init_repo` reports
  the feature validation failure and keeps the checkpoint for remediation.

## Migration Plan

Newly synced `panopticon-init` skills use the viable continuation path. Existing
stale checkpoints resume normally when the child receives the updated skill and
runs initialization again. No data migration is required.
