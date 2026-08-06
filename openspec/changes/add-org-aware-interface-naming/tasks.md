# Organization-aware interface naming tasks

## 1. Configuration and instance-index access

- [x] 1.1 Extend child `panopticon/config.json` parsing and saving with an optional,
  validated `gating.interface-conflict` override while preserving it during
  initialization and re-initialization.
- [x] 1.2 Add a single effective-gating resolver with child override, instance
  configuration, and advisory-default precedence; return the value and its
  source for report rendering.
- [x] 1.3 Implement a reusable, validated local-generation loader for the
  instance compiled interface index, preferring a supplied checkout and using
  authenticated configured-instance retrieval otherwise; distinguish a fresh
  missing index from retrieval and validation failures.
- [x] 1.4 Add configuration and index-loader unit tests for valid and invalid
  child overrides, precedence, fresh instances, unavailable indexes, and
  malformed indexes.

## 2. Organization-aware local naming and documentation generation

- [x] 2.1 Extend the interface-naming guidance with evidence-led,
  organization-scale rules: technology-function shared resources,
  durable-owner local surfaces, and distinct contracts on a shared backend.
- [x] 2.2 Update the documentation-generation and initialization guidance so
  documentation generation loads the instance index, makes local naming
  judgments, writes only reviewed source/configuration hints, regenerates the
  local index, and then renders index-derived documentation.
- [x] 2.3 Add deterministic tooling boundaries that preserve hint-first
  extraction and make repeated extraction, simulation, and compilation
  independent of the LLM and instance index after a local judgment is saved.
- [x] 2.4 Add naming and extraction tests for existing-name reuse, generic raw
  names becoming organization-scale names, distinct local same-type resources,
  existing user hints, ambiguous evidence, and deterministic re-extraction.

## 3. PR candidate analysis, report visualization, and gating

- [x] 3.1 Implement bounded deterministic selection of relevant instance-index
  candidates for proposed child interfaces and a provider-neutral structured
  LLM evaluation that labels likely matches, likely distinctions, or
  insufficient evidence without mutating any index or hint.
- [x] 3.2 Extend the combined PR report model and action handling with
  candidate-analysis findings, deterministic prospective-merge results, and
  effective conflict-policy provenance.
- [x] 3.3 Extract and validate the child architecture overview's Mermaid block
  for the marker-owned Panopticon PR report, rendering an explicit unavailable
  state when the existing diagram check cannot supply a valid block.
- [x] 3.4 Update every provider reusable PR workflow to run candidate analysis,
  resolve the effective child-or-instance gating mode, post the prominent
  warning in both modes, fail only when the effective mode is blocking, and
  update the maintained report comment rather than the PR description.
- [x] 3.5 Add unit and workflow-contract tests for candidate context bounds,
  advisory-only and blocking behavior, child-over-instance precedence,
  prominent warnings, Mermaid report content, unavailable diagrams, and no
  index mutation by CI.

## 4. Migration guidance and verification

- [x] 4.1 Document the controlled migration of existing generic names through
  child documentation-refresh PRs, reviewed hints, regenerated shards, and
  prospective merge reports; document how child repositories select a blocking
  override.
- [x] 4.2 Run the focused Python tests, provider-workflow contract tests,
  OpenSpec validation, and Markdown linting required by the changed artifacts.
- [x] 4.3 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
