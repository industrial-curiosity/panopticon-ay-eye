# Agent runtime OpenAI provider delta

## MODIFIED Requirements

### Requirement: Provider-agnostic LLM configuration for CI

The agent runtime SHALL remain the execution path for LLM tasks in CI workflows
only. Its prompting, structured-response validation, correction loop, bounded
transport retry behavior, and public client surface SHALL remain
provider-neutral. The selected reusable provider workflow SHALL translate its
canonical inputs and secrets into the runtime configuration required by its
adapter. The LiteLLM and OpenAI adapters SHALL preserve the existing
OpenAI-compatible `/chat/completions` request and response behavior. The Bedrock
adapter SHALL use AWS Bedrock Converse with OIDC-provided temporary credentials
and provider-native message, response, and error mapping. A provider adapter
MAY use a narrowly scoped, pinned, CI-only SDK; provider SDKs MUST NOT become a
dependency of child-vendored tooling or local agent flows.

#### Scenario: Configured LiteLLM workflow

- **WHEN** a child invokes the selected LiteLLM reusable workflow with a
  reachable endpoint, valid API key, and model input
- **THEN** the runtime completes requests using the existing OpenAI-compatible
  request and response semantics

#### Scenario: Configured OpenAI workflow

- **WHEN** a child invokes the selected OpenAI reusable workflow with a
  reachable OpenAI endpoint, valid OpenAI Platform API key, and model input
- **THEN** the runtime completes requests using the same OpenAI-compatible
  request and response semantics while identifying the provider as OpenAI

#### Scenario: Configured Bedrock workflow

- **WHEN** a child invokes the selected Bedrock reusable workflow with a valid
  OIDC role, AWS region, and Converse-compatible model identifier
- **THEN** the runtime completes requests through Bedrock Converse while
  retaining the same shared prompting, retry, validation, and exception
  contracts

#### Scenario: Provider-specific dependency remains CI-only

- **WHEN** the Bedrock adapter introduces a pinned AWS SDK dependency
- **THEN** only the Bedrock CI workflow installs it and no child bootstrap or
  local agent flow requires it
