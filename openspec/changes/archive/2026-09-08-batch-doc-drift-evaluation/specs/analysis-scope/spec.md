# Analysis-scope changes

## ADDED Requirements

### Requirement: Managed Panopticon metadata SHALL be excluded from doc-drift scope

Doc-drift input preparation SHALL classify `panopticon/`, `.github/`, and
`.agents/` as repository metadata and exclude them before behavior-path
selection, batch planning, or evaluator prompt construction. This exclusion
applies even when a managed path contains code or configuration.

#### Scenario: Managed metadata-only pull request

- **WHEN** a pull request changes only paths under `panopticon/`, `.github/`,
  `.agents/`, and documentation paths
- **THEN** doc drift returns a clean verdict without an LLM request
