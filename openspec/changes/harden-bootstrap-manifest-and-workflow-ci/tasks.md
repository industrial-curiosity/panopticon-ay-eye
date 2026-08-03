# Implementation Tasks

## 1. Authoritative local-tooling manifest

- [x] 1.1 Replace the Python local-tooling manifest with the versioned JSON
  manifest and implement strict, data-only validation in bootstrap.
- [x] 1.2 Make bootstrap fetch the selected-ref manifest and stage every listed
  module before writing any managed tooling; remove the manifest import that
  breaks the default payload loader.
- [x] 1.3 Update local sync to parse the selected-ref JSON manifest without
  executing it, preserve preview and unmanaged-file behavior, and stage the
  full selected module set before writing.
- [x] 1.4 Update tooling-currency to parse the instance checkout's JSON
  manifest, compare only manifest-owned modules, and warn without failing on
  an invalid manifest.

## 2. Workflow-contract CI enforcement

- [x] 2.1 Add deterministic reusable-workflow discovery to
  `panopticon.workflow_contracts` while preserving explicit-path validation.
- [x] 2.2 Add a credential-free template-validation workflow for pull requests,
  pushes, and manual dispatch that runs discovery-based contract validation and
  the full Python suite.

## 3. Regression coverage and verification

- [x] 3.1 Add bootstrap, launcher, sync, and tooling-currency tests for the
  selected-ref JSON manifest, malformed input, atomic staging, advisory
  invalid-manifest handling, and unchanged child-owned files.
- [x] 3.2 Add workflow-contract tests for discovery of every shipped reusable
  workflow, deterministic error reporting, and a newly discovered workflow.
- [x] 3.3 Run focused tests, the full Python suite, reusable-workflow contract
  validation, strict OpenSpec validation, and Markdown structure checks.

## 4. Documentation

- [x] 4.1 Update `docs/testing.md`, `docs/setup-guide.md`, `PANOPTICON.md`, and
  the rollout-hardening status ledger with the JSON manifest and template CI
  validation procedure.
- [x] 4.2 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
