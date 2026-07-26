## 1. Shared caller reconciliation

- [ ] 1.1 Extract or expose the existing managed-caller generation contract so
  bootstrap and local sync use identical workflow text.
- [ ] 1.2 Fetch and validate the instance provider configuration at the child's
  configured workflow ref before generating callers.
- [ ] 1.3 Extend local sync's comparison and default-write paths to reconcile
  every managed caller, including a missing resource-sync caller.

## 2. Verification

- [ ] 2.1 Add local-sync tests for missing/stale callers, dry-run reporting and
  no-write behavior, provider-specific caller generation, and invalid instance
  configuration.
- [ ] 2.2 Add bootstrap/sync parity coverage proving identical caller output
  from the same child and instance configuration.
- [ ] 2.3 Update docs/testing.md and run focused tests plus strict OpenSpec
  validation.

## 3. Documentation

- [ ] 3.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
