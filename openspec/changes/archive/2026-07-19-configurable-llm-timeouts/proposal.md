# Configurable LLM timeouts

## Why

The CI LLM client currently has fixed request and retry limits, while the
workflow has no explicit time budget. A slow but healthy organization-specific
model can fail too early, while a broken endpoint can consume an unnecessarily
long CI run.

## What Changes

- Add org-level configuration for the CI LLM request timeout, transport retry
  budget, JSON-correction retry budget, and workflow job time limit.
- Use defaults of 90 seconds per LLM request, two transport attempts, two
  JSON-correction retries, and a 20-minute PR-evaluation job limit.
- Validate configured values before LLM-dependent checks run and fail clearly
  when a value is malformed or outside a safe bound.
- Document the configuration and its relationship to an upstream LiteLLM proxy
  timeout.

## Capabilities

### New Capabilities

- `llm-timeout-configuration`: Configures bounded LLM request and retry behavior
  for an organization’s CI workflows.

### Modified Capabilities

- `agent-runtime`: The CI LLM runtime must consume validated timeout and retry
  configuration.
- `pr-evaluation`: The reusable PR-evaluation workflow must expose an explicit,
  configurable overall job budget.

## Impact

Affected areas include `panopticon/llm.py`, LLM runtime tests, the reusable PR
workflow, initialization/configuration validation, setup documentation, and the
agent-runtime and PR-evaluation specifications. No provider SDK or
provider-specific request field is introduced.
