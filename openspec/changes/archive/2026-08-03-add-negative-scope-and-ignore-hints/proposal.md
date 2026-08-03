# Add deterministic negative scope and ignore hints

## Why

Panopticon currently scans illustrative material alongside production code, so examples,
fixtures, and scaffolds can create false interface, dependency, and documentation-drift
findings. Maintainers also lack a deterministic, reviewable way to exclude unusual
illustrative material without relying on prompts or manual cleanup.

## What Changes

- Add one deterministic analysis-scope policy used by parser iteration, interface and
  dependency LLM fallback selection, and doc-drift input preparation.
- Exclude only exact illustrative directory names: `examples`, `samples`, `fixtures`,
  `testdata`, `demos`, `scaffolding`, `demo`, and `scaffold`.
- Add explicit `panopticon-ignore file` and `panopticon-ignore declaration` hints.
- Report every excluded path or declaration and its exclusion reason in command and CI
  summaries.
- Add a machine-maintained analysis-scope section to each repository's operational
  documentation, listing the illustrative directories actually excluded in that repository.
- Link the architecture overview directly below its diagram to the analysis-scope section.

## Capabilities

### New Capabilities

- `analysis-scope`: Deterministically classify repository paths and declarations as in
  or out of Panopticon analysis scope, with explicit, reviewable exclusion reasons.

### Modified Capabilities

- `interface-indexing`: Exclude out-of-scope material before deterministic and LLM
  interface extraction.
- `dependency-indexing`: Exclude out-of-scope material before deterministic and LLM
  dependency extraction.
- `doc-generation`: Render and link the per-repository analysis-scope documentation.
- `architecture-diagrams`: Link each repository architecture diagram to its
  operational analysis-scope section.

## Impact

This changes shared parser iteration, extraction drivers, doc-drift preparation,
documentation templates, agent guidance, and their focused tests. It adds no runtime
dependencies, network calls, or index-schema fields.
