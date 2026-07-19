# Agent runtime delta

## MODIFIED Requirements

### Requirement: Provider-agnostic LLM configuration for CI

The agent runtime SHALL remain the execution path for LLM tasks in CI workflows only. Its prompting,
structured-response validation, correction loop, bounded transport retry behavior, and public client
surface SHALL remain provider-neutral. The selected reusable provider workflow SHALL translate its
canonical inputs and secrets into the runtime configuration required by its adapter. The LiteLLM adapter
SHALL preserve the existing OpenAI-compatible `/chat/completions` request and response behavior. The
Bedrock adapter SHALL use AWS Bedrock Converse with OIDC-provided temporary credentials and provider-native
message, response, and error mapping. A provider adapter MAY use a narrowly scoped, pinned, CI-only SDK;
provider SDKs MUST NOT become a dependency of child-vendored tooling or local agent flows.

#### Scenario: Configured LiteLLM workflow

- **WHEN** a child invokes the selected LiteLLM reusable workflow with a reachable endpoint, valid API
  key, and model input
- **THEN** the runtime completes requests with the existing OpenAI-compatible transport and shared client
  semantics

#### Scenario: Configured Bedrock workflow

- **WHEN** a child invokes the selected Bedrock reusable workflow with a valid OIDC role, AWS region, and
  Converse-compatible model identifier
- **THEN** the runtime completes requests through Bedrock Converse while retaining the same shared
  prompting, retry, validation, and exception contracts

#### Scenario: Provider-specific dependency remains CI-only

- **WHEN** the Bedrock adapter introduces a pinned AWS SDK dependency
- **THEN** only the Bedrock CI workflow installs it and no child bootstrap or local agent flow requires it

### Requirement: Fail loudly on missing requirements

The selected provider workflow and runtime SHALL fail with a clear error naming every missing, invalid,
unreachable, or incapable requirement of an LLM-dependent CI step. Errors SHALL identify each item by its
configured org-level secret or variable name where applicable, distinguish missing configuration from an
unusable provider runtime, and point at complete setup or child-bootstrap recovery instructions.
LLM-dependent checks MUST NOT silently skip, fall back to another provider, or report success.

#### Scenario: LiteLLM endpoint variable not configured

- **WHEN** a LiteLLM caller supplies no value from the configured endpoint variable name
- **THEN** the workflow fails, names that configured variable, and points at the provider setup
  instructions

#### Scenario: Bedrock runtime lacks Converse support

- **WHEN** the Bedrock provider dependency resolves successfully but its client lacks the required
  Converse capability
- **THEN** preflight fails before any LLM check, naming the resolved dependency version and import path
  plus the corrective installation path

#### Scenario: Endpoint unreachable mid-run

- **WHEN** an LLM request through the selected provider still fails after retries
- **THEN** the workflow fails, reporting the selected provider, interrupted check, and failure reason

## ADDED Requirements

### Requirement: Provider adapters preflight their runtime

Each provider adapter SHALL expose a preflight that runs after provider setup and before the first
LLM-dependent check. The preflight SHALL verify provider-relevant runtime capabilities without duplicating
the check in every consumer. Failure SHALL use the same loud operational-failure contract as missing
configuration.

#### Scenario: Bedrock SDK is too old

- **WHEN** the installed AWS SDK cannot construct a client with the Converse operation
- **THEN** one centralized preflight fails before doc-drift or index-currency runs
