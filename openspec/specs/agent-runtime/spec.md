### Requirement: Provider-agnostic LLM configuration for CI

The agent runtime is the execution path for LLM tasks in CI workflows only. It SHALL read the LLM endpoint
from `PANOPTICON_LLM_ENDPOINT` (an org-level Actions **variable**), the API key from `PANOPTICON_LLM_API_KEY`
(an org-level Actions **secret**), and the optional model name from `PANOPTICON_LLM_MODEL` (an org-level
Actions **variable**, defaulting to `default`). It SHALL speak the OpenAI-compatible `/chat/completions`
request shape so that any litellm-compatible endpoint works. The runtime MUST NOT depend on provider-specific
SDKs or hardcode any provider.

#### Scenario: Configured litellm endpoint

- **WHEN** `PANOPTICON_LLM_ENDPOINT` (variable) and `PANOPTICON_LLM_API_KEY` (secret) are set to a reachable
  litellm-compatible endpoint
- **THEN** the runtime completes chat requests against it without any provider-specific code path

#### Scenario: Switching providers requires no code change

- **WHEN** an org repoints `PANOPTICON_LLM_ENDPOINT` at a different litellm-compatible endpoint
- **THEN** all agent-dependent workflows continue to function with no changes to workflows or tooling

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

The workflow SHALL fail with a clear error naming exactly what is missing and how to provide it whenever
`PANOPTICON_LLM_ENDPOINT`, `PANOPTICON_LLM_API_KEY`, or any other requirement of an LLM-dependent CI step is
missing or unreachable. Error messages SHALL distinguish whether the missing item is an org-level secret or an
org-level variable and SHALL point at the setup instructions. LLM-dependent checks MUST NOT silently skip or
report success.

#### Scenario: Endpoint variable not configured

- **WHEN** a PR workflow runs in a repo without `PANOPTICON_LLM_ENDPOINT` org variable configured
- **THEN** the workflow fails, naming the missing variable and pointing at the setup instructions

#### Scenario: Endpoint unreachable mid-run

- **WHEN** an LLM request still fails after retries during a check
- **THEN** the workflow fails, reporting which check was interrupted and the failure reason

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
