# Implementation tasks

## 1. Shared LLM diagnostics

- [ ] 1.1 Add a provider-neutral, non-secret request diagnostic record to `panopticon.llm` for successful and failed request attempt sequences.
- [ ] 1.2 Render available request diagnostics in doc-drift and index-currency reports, including the no-request case.
- [ ] 1.3 Add LLM and report tests covering success, timeout, and pre-request configuration failure without sensitive fields.

## 2. Conservative doc-drift context selection

- [ ] 2.1 Implement deterministic doc-drift context selection that excludes rendered interfaces, includes architecture and operations, and selects component docs by explicit changed-path references.
- [ ] 2.2 Implement the all-component bounded fallback when any behavior-bearing path has no deterministic component-document match.
- [ ] 2.3 Add doc-drift tests for targeted selection, conservative fallback, no behavior-bearing paths, byte-budget behavior, and reported selection diagnostics.

## 3. Compact workflow annotations

- [ ] 3.1 Change LLM-backed check CLIs and their workflow wrapper steps to retain plain diagnostics, exit codes, and report files without emitting duplicate GitHub error commands.
- [ ] 3.2 Update LiteLLM, OpenAI, and Bedrock PR workflows so final gating emits the single Panopticon-authored operational-failure annotation after combined reporting.
- [ ] 3.3 Extend workflow and report tests to prove independent checks still run, operational failures remain blocking, and duplicate annotations are absent.

## 4. Aggregated tooling-currency warnings

- [ ] 4.1 Add a renderable tooling-currency finding summary that preserves individual findings for the step summary.
- [ ] 4.2 Update all provider PR workflows to append tooling details to the job summary and emit one advisory warning with count and sync recovery guidance.
- [ ] 4.3 Add tooling-currency and provider-workflow tests for clean output, one-warning aggregation, summary detail, and unchanged advisory behavior.

## 5. Documentation and validation

- [ ] 5.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
- [ ] 5.2 Run the focused Python and workflow-contract test suites, then the full test suite and OpenSpec validation.
