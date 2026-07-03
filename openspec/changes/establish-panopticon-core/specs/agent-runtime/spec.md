## ADDED Requirements

### Requirement: Provider-agnostic LLM configuration for CI

The agent runtime is the execution path for LLM tasks in CI workflows only. It SHALL read the LLM endpoint
from `PANOPTICON_LLM_ENDPOINT` and the API key from `PANOPTICON_LLM_API_KEY`, and SHALL speak the
OpenAI-compatible `/chat/completions` request shape so that any litellm-compatible endpoint works. The runtime
MUST NOT depend on provider-specific SDKs or hardcode any provider.

#### Scenario: Configured litellm endpoint

- **WHEN** `PANOPTICON_LLM_ENDPOINT` and `PANOPTICON_LLM_API_KEY` are set to a reachable litellm-compatible
  endpoint
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
missing or unreachable. LLM-dependent checks MUST NOT silently skip or report success.

#### Scenario: Endpoint not configured

- **WHEN** a PR workflow runs in a repo without `PANOPTICON_LLM_ENDPOINT` configured
- **THEN** the workflow fails, naming the missing secret and pointing at the setup instructions

#### Scenario: Endpoint unreachable mid-run

- **WHEN** an LLM request still fails after retries during a check
- **THEN** the workflow fails, reporting which check was interrupted and the failure reason
