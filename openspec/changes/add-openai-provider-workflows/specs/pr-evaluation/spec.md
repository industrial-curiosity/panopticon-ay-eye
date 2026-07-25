# PR evaluation OpenAI provider delta

## MODIFIED Requirements

### Requirement: Separate provider workflows preserve the PR evaluation contract

The template SHALL ship independent LiteLLM, OpenAI, and Bedrock reusable PR
workflows. Each SHALL own its provider setup, authentication, dependency
installation, preflight, canonical inputs and secrets, and complete PR
evaluation job. All workflows MUST preserve the existing initialization,
independent-check execution, reporting, gating, simulation, and branch-push
contracts. The OpenAI workflow SHALL be a correctly named clone of the LiteLLM
workflow's behavior, SHALL fix `PANOPTICON_LLM_PROVIDER` to `openai`, and SHALL
use OpenAI labels in its workflow name, summaries, and errors. Provider-
independent merge and PR-close workflows SHALL remain shared.

#### Scenario: OpenAI child evaluates a pull request

- **WHEN** an initialized child caller selects the OpenAI provider and supplies
  its configured key, model, instance token, and budget values
- **THEN** the OpenAI reusable workflow runs every configured PR check and
  applies the same configured gate outcomes as the LiteLLM reusable workflow
  using the fixed `https://api.openai.com/v1` endpoint

#### Scenario: LiteLLM PR evaluation

- **WHEN** a correctly wired LiteLLM child opens or updates a PR
- **THEN** the LiteLLM workflow runs the complete existing PR evaluation
  contract without AWS setup

#### Scenario: Bedrock PR evaluation

- **WHEN** a correctly wired Bedrock child opens or updates a PR
- **THEN** the Bedrock workflow obtains credentials through the selected trusted
  credential mode, installs its isolated dependency, preflights Converse, and
  then runs the same complete PR evaluation contract

#### Scenario: OpenAI provider configuration is missing

- **WHEN** an OpenAI caller omits a configured API key, model, or instance token
- **THEN** the OpenAI workflow fails before LLM work, identifies the configured
  Actions name and OpenAI provider, and provides exact instance-configuration
  and child-bootstrap recovery guidance
