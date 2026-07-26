## 1. Shared caller reconciliation

- [x] 1.1 Replace the local-tooling module allowlist with staged reconciliation
  of the managed `panopticon/` directory and explicit protected paths, without
  deleting any child file.
- [x] 1.2 Move the caller workflow list and renderer into one shared module
  used by both bootstrap and sync after directory staging.
- [x] 1.3 Reconcile managed workflow callers while preserving child-owned
  workflow files.

## 2. Verification

- [x] 2.1 Add tests for staged directory updates, new sync dependencies,
  protected files, child-owned workflow preservation, and no deletion when a
  source resource disappears.
- [x] 2.2 Add bootstrap/sync parity coverage using the single shared caller
  contract.
- [x] 2.3 Update docs/testing.md and run focused tests plus strict OpenSpec
  validation.

## 3. Documentation

- [x] 3.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
