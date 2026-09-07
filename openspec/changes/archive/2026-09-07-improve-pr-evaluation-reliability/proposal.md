# Improve PR-evaluation reliability

## Why

One timed-out doc-drift request currently creates several GitHub error annotations, while every tooling-currency finding creates its own warning. The doc-drift request also sends all documentation within a broad byte cap, which makes its latency and timeout behavior hard to predict or diagnose.

## What Changes

- Centralize blocking operational-failure annotations in the final PR-workflow gate while retaining each check's detailed combined-report section and exit-code contract.
- Emit one advisory tooling-currency annotation per run and preserve the individual findings in the step summary.
- Select only the documentation relevant to behavior-bearing changed paths for doc-drift LLM input, with a deterministic bounded fallback when relevance cannot be established.
- Record safe per-request diagnostics for LLM-backed CI checks: provider, model, input size, attempt count, elapsed duration, and outcome class. Never record credentials, prompt content, or resolved secret values.

## Capabilities

### New Capabilities

- `llm-check-diagnostics`: Safe, actionable diagnostics for LLM-backed CI check requests and failures.

### Modified Capabilities

- `pr-evaluation`: PR evaluation emits one blocking operational-failure annotation and scopes doc-drift context to the changed behavior.
- `tooling-currency`: Advisory tooling-currency findings are aggregated into one warning while their file-level details remain available in the step summary.

## Impact

- Affected workflow files: all provider-specific reusable PR evaluation workflows.
- Affected Python tooling: `panopticon/drift.py`, `panopticon/llm.py`, `panopticon/tooling_currency.py`, and supporting report helpers as needed.
- Affected tests: workflow, doc-drift, LLM runtime, tooling-currency, and report tests.
- Affected documentation: `README.md` and `docs/spec.md`.
