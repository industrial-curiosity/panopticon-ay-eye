# Bootstrap provider loader tasks

## 1. Repair default payload loading

- [ ] 1.1 Load and register `panopticon.providers` before executing the default
  bootstrap payload.
- [ ] 1.2 Preserve the existing validated GitHub-contents retrieval and
  in-memory package-loading behavior.

## 2. Add regression coverage

- [ ] 2.1 Update the self-bootstrap test payload to import the provider registry
  and assert that the loader retrieves it.
- [ ] 2.2 Add coverage for an invalid provider-module payload failing before
  bootstrap execution.
- [ ] 2.3 Run focused bootstrap tests and the repository validation suite.

## 3. Update documentation

- [ ] 3.1 Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes introduced by this change.
