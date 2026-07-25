# Bootstrap provider loader tasks

## 1. Repair default payload loading

- [x] 1.1 Load and register `panopticon.providers` before executing the default
  bootstrap payload.
- [x] 1.2 Preserve the existing validated GitHub-contents retrieval and
  in-memory package-loading behavior.

## 2. Add regression coverage

- [x] 2.1 Update the self-bootstrap test payload to import the provider registry
  and assert that the loader retrieves it.
- [x] 2.2 Add coverage for an invalid provider-module payload failing before
  bootstrap execution.
- [x] 2.3 Run focused bootstrap tests and the repository validation suite.

## 3. Update documentation

- [x] 3.1 Review README.md and docs/spec.md; no update is required because the
  repair is internal to the existing bootstrap mechanism.
