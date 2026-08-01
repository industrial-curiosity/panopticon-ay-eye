# Organization interface-conflict visibility tasks

## 1. Compile potential collisions

- [x] 1.1 Extend compiled-index conflict validation and deterministic ordering
  for `potential-name-collision` findings.
- [x] 1.2 Detect disjoint same-name/type-mismatch repository sets during index
  compilation while preserving overlapping type migrations.
- [x] 1.3 Keep shard reconstruction, merge simulation, reporting, and issue
  preparation compatible with the derived multi-type conflict.

## 2. Render complete organization interface inventory and conflict visibility

- [x] 2.1 Render every participating repository's interface resources in the
  organization document, including single-repository resources, while retaining
  external-only dependency rendering.
- [x] 2.2 Add the conditional `## Detected interface conflicts` summary and
  derive per-resource conflict targets from the compiled index.
- [x] 2.3 Render interface resources as Mermaid nodes; style conflicted nodes
  bold red and mark their relationship-table entries with a red-circle indicator
  and bold Markdown.

## 3. Verify deterministic behavior

- [x] 3.1 Add index and merge tests for potential-collision creation,
  non-creation for overlapping migrations, removal, and round-trip parity.
- [x] 3.2 Add organization-diagram tests for standalone interfaces, the exact
  conflict heading, summary details, Mermaid styling, table emphasis, clean
  output, and deterministic rendering.
- [x] 3.3 Update docs/testing.md with the added test coverage and run the
  focused suite plus strict OpenSpec validation.

## 4. Documentation

- [x] 4.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
