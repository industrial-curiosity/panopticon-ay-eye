# Prevent doc-drift false positives

## Why

PR #6 in a child repository updated both the documentation-generation guidance
and its architecture document's org-diagram link, yet the doc-drift check
reported that the same architecture document was stale. The report also marked
an unaffected component document stale while stating that no update was needed.

## What Changes

- Require doc-drift to pass when a PR already updates the relevant
  documentation consistently with its behavior change.
- Constrain doc-drift findings to documentation that the PR diff can support;
  contradictory or unsupported findings become operational failures rather than
  merge-blocking stale verdicts.
- Clarify the doc-drift skill's treatment of template and documentation-
  generation guidance changes, and add regression coverage for this case.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `doc-generation`: make LLM-based doc-drift verdicts evidence-backed and
  prevent false stale findings when relevant docs are updated in the same PR.

## Impact

The doc-drift skill, `panopticon.drift` verdict validation and reporting,
provider PR workflows' handling of invalid verdicts, and doc-drift regression
tests are affected. No new dependency or external API is required.
