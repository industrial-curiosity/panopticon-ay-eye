# Agent runtime

## Purpose

Define the provider-agnostic LLM runtime used by Panopticon CI checks.

## Requirements

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

### Requirement: Local execution through the user's agent harness

LLM-dependent local tasks (child-repo initialization doc generation and subsequent doc updating) SHALL be
executable as skills in the user's preferred AI agent harness, and local execution MUST NOT require
`PANOPTICON_LLM_ENDPOINT` or `PANOPTICON_LLM_API_KEY` to be configured. Only CI workflows SHALL depend on the
runtime's endpoint/key configuration.

#### Scenario: Local initialization without Panopticon LLM configuration

- **WHEN** a user runs initialization locally through their own agent harness with no `PANOPTICON_LLM_*`
  variables set
- **THEN** doc generation and other LLM-dependent initialization steps complete through the harness using the
  bundled skills

#### Scenario: CI uses the configured runtime

- **WHEN** an LLM-dependent check runs in a CI workflow
- **THEN** it executes through the runtime configured via `PANOPTICON_LLM_ENDPOINT` and
  `PANOPTICON_LLM_API_KEY`

### Requirement: Skill-based prompting

The runtime SHALL load agent instructions from the same markdown skill files that drive local harness
execution and pass them as system-prompt content, so that agent behavior is versioned once and shared between
CI and local flows.

#### Scenario: Skill loaded for a doc-generation call

- **WHEN** a workflow invokes the runtime for a task with an associated skill file
- **THEN** the skill file's content is included as system-prompt content for that request

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

### Requirement: Provider adapters preflight their runtime

Each provider adapter SHALL expose a preflight that runs after provider setup and before the first
LLM-dependent check. The preflight SHALL verify provider-relevant runtime capabilities without duplicating
the check in every consumer. Failure SHALL use the same loud operational-failure contract as missing
configuration.

#### Scenario: Bedrock SDK is too old

- **WHEN** the installed AWS SDK cannot construct a client with the Converse operation
- **THEN** one centralized preflight fails before doc-drift or index-currency runs

### Requirement: Structured-response retry for non-compliant model output

The runtime SHALL, for any CI check that requires a structured (JSON) response — the doc-drift,
index-currency, and interface-extraction checks — use a single shared runtime method that validates
the response against the check's expected shape and, on a parse or validation failure, retries with
a corrective message appended to the conversation before failing loudly. The retry budget SHALL be
small and bounded; exhausting it SHALL raise the same loud, exit-code-visible operational failure
this runtime already guarantees for missing configuration (see "Fail loudly on missing
requirements") — a check MUST NOT silently accept a response that failed validation, and MUST NOT
retry indefinitely. This behavior SHALL work against any litellm-compatible endpoint with no
provider-specific request parameters, consistent with "Provider-agnostic LLM configuration for CI."

#### Scenario: Non-compliant response is corrected on retry

- **GIVEN** a check requests a structured JSON response and the model's first response is prose
  that fails to parse as JSON
- **WHEN** the runtime retries with a corrective message
- **THEN** a second, compliant response is parsed and validated successfully, and the check
  proceeds normally with no operational failure

#### Scenario: Persistently non-compliant response fails loudly after the retry budget is exhausted

- **GIVEN** a model's response fails to parse or validate on every attempt
- **WHEN** the runtime exhausts its bounded retry budget
- **THEN** the check fails with an operational-failure error identifying which check it was and
  that the response was not the expected shape — the check never silently proceeds with malformed
  or partial data

#### Scenario: A validation failure is corrected on retry, not only a syntactic parse failure

- **GIVEN** a model's response is syntactically valid JSON but is missing a required field or has
  a field of the wrong type
- **WHEN** the runtime retries with a corrective message describing the specific validation problem
- **THEN** the retry can succeed with a shape-correct response, the same recovery path as a
  syntactic parse failure

#### Scenario: No provider-specific structured-output parameters are required

- **WHEN** the runtime sends a structured-response request, including any corrective retry
- **THEN** the request payload uses the same OpenAI-compatible `/chat/completions` shape as any
  other request — no `response_format` or other provider-specific field is required for retry and
  validation to work
