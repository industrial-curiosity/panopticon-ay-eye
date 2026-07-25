# Default optional LLM environment variables

## Why

Optional LLM request-budget variables are currently defaulted for the primary
job environment but can reach individual check steps as empty strings. The
runtime treats empty values as invalid overrides, so a repository that omits
`PANOPTICON_LLM_TIMEOUT_SECONDS` can fail instead of using its documented
default.

## What Changes

- Apply documented defaults for every optional LLM request-budget variable at
  every provider-workflow execution point where the variable is consumed.
- Preserve validation and loud failures for variables that are explicitly set
  to blank, non-integer, or out-of-range values when that distinction is
  available at the workflow boundary.
- Add regression coverage for absent optional variables across both built-in
  provider workflows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `llm-timeout-configuration`: Ensure unset optional request-budget variables
  consistently receive their documented defaults throughout a provider
  workflow.

## Impact

- Provider reusable workflows for LiteLLM and Bedrock.
- Workflow and runtime configuration tests.
- Configuration documentation if implementation changes the documented
  behavior or recovery guidance.
