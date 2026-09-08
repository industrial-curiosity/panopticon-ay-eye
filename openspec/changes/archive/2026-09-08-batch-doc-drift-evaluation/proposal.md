# Batch doc-drift evaluation

## Why

Doc drift currently sends one full behavior-bearing pull-request diff to the
LLM. Repository metadata can inflate that request without changing child
architecture, and a large request can exhaust the configured timeout even when
the provider is healthy for smaller checks.

## What Changes

- Exclude Panopticon-managed repository metadata from doc-drift behavior scope.
- Plan minimal doc-drift evaluation batches from relevant product changed paths
  and documentation paths before sending any patch contents to the LLM.
- Evaluate each planned batch independently and combine its stale findings into
  the existing doc-drift verdict and report.
- Stop immediately on a planning or evaluation timeout and report the failed
  stage, bounded input details, and concrete PR-size and timeout remedies.

## Capabilities

### New Capabilities

- `batched-doc-drift-evaluation`: Plan and evaluate minimal, isolated
  doc-drift LLM batches for product behavior changes.

### Modified Capabilities

- `analysis-scope`: Exclude Panopticon-managed metadata from doc-drift input.
- `doc-generation`: Define batched doc-vs-code drift behavior and combined
  verdict requirements.
- `llm-check-diagnostics`: Add stage and recovery guidance to timeout reports.
- `pr-evaluation`: Replace single-prompt doc context selection with planned
  batch evaluation while retaining existing operational-failure gating.

## Impact

- Affected tooling: `panopticon/drift.py`, `panopticon/report.py`, the
  `panopticon-doc-drift` skill, and their unit tests.
- Existing reusable PR workflows and provider contracts remain unchanged.
- Child-repository managed metadata changes no longer trigger doc-drift LLM
  requests.
