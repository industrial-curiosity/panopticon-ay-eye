# Agent runtime timeout configuration changes

## MODIFIED Requirements

### Requirement: Provider-agnostic LLM configuration for CI

The agent runtime is the execution path for LLM tasks in CI workflows only. It
SHALL read the LLM endpoint from `PANOPTICON_LLM_ENDPOINT` (an org-level Actions
**variable**), the API key from `PANOPTICON_LLM_API_KEY` (an org-level Actions
**secret**), and the optional model name from `PANOPTICON_LLM_MODEL` (an
org-level Actions **variable**, defaulting to `default`). It SHALL read its
optional request budget from `PANOPTICON_LLM_TIMEOUT_SECONDS`,
`PANOPTICON_LLM_MAX_ATTEMPTS`, and `PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS`
(org-level Actions **variables**) using the defaults and validation defined by
the LLM timeout configuration capability. It SHALL speak the OpenAI-compatible
`/chat/completions` request shape so that any litellm-compatible endpoint works.
The runtime MUST NOT depend on provider-specific SDKs or hardcode any provider.

#### Scenario: Configured litellm endpoint

- **WHEN** `PANOPTICON_LLM_ENDPOINT` (variable) and `PANOPTICON_LLM_API_KEY`
  (secret) are set to a reachable litellm-compatible endpoint
- **THEN** the runtime completes chat requests against it without any
  provider-specific code path

#### Scenario: Switching providers requires no code change

- **WHEN** an org repoints `PANOPTICON_LLM_ENDPOINT` at a different
  litellm-compatible endpoint
- **THEN** all agent-dependent workflows continue to function with no changes to
  workflows or tooling

#### Scenario: Configured timeout remains provider-agnostic

- **WHEN** an organization changes its configured LLM request timeout while
  using any supported litellm-compatible endpoint
- **THEN** the runtime applies the timeout through its shared HTTP client
  without adding a provider-specific request field
