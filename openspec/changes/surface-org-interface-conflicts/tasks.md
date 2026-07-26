# Organization interface-conflict visibility tasks

## 1. Compile potential collisions

- [ ] 1.1 Extend compiled-index conflict validation and deterministic ordering
  for `potential-name-collision` findings.
- [ ] 1.2 Detect disjoint same-name/type-mismatch repository sets during index
  compilation while preserving overlapping type migrations.
- [ ] 1.3 Keep shard reconstruction, merge simulation, reporting, and issue
  preparation compatible with the derived multi-type conflict.

## 2. Render organization conflict visibility

- [ ] 2.1 Add the conditional `## Detected interface conflicts` summary to the
  generated organization architecture document.
- [ ] 2.2 Derive per-resource conflict targets and render affected Mermaid
  resources as bold, red styled nodes.
- [ ] 2.3 Mark affected relationship-table resource names with a red-circle
  indicator and bold Markdown while leaving clean rows unchanged.

## 3. Verify deterministic behavior

- [ ] 3.1 Add index and merge tests for potential-collision creation,
  non-creation for overlapping migrations, removal, and round-trip parity.
- [ ] 3.2 Add organization-diagram tests for the exact conflict heading,
  summary details, Mermaid styling, table emphasis, clean output, and
  deterministic rendering.
- [ ] 3.3 Update docs/testing.md with the added test coverage and run the
  focused suite plus strict OpenSpec validation.

## 4. Documentation

- [ ] 4.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
