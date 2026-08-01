# Reusable Workflow Contract Validation

## ADDED Requirements

### Requirement: Provider reusable workflows have validated caller contracts

The template SHALL deterministically validate every shipped LiteLLM, OpenAI,
and Bedrock reusable PR workflow against its `on.workflow_call` caller
contract. The validation SHALL report every dot-form `inputs.<name>` or
`secrets.<name>` expression reference that lacks a declaration in the matching
`workflow_call.inputs` or `workflow_call.secrets` mapping, and SHALL not
require a third-party YAML parser or GitHub-hosted service.

#### Scenario: Shipped provider workflow has a complete contract

- **WHEN** repository validation examines a shipped provider reusable PR
  workflow whose input and secret references are declared
- **THEN** it reports no contract errors

#### Scenario: Reusable workflow references an undeclared caller value

- **WHEN** repository validation examines a reusable workflow containing
  `inputs.endpoint` or `secrets.api_key` without the matching declaration
- **THEN** it reports that undeclared reference as a contract error before
  release

#### Scenario: Bedrock workflow is isolated from LiteLLM caller configuration

- **WHEN** repository validation examines the Bedrock reusable PR workflow
- **THEN** it finds no reference to LiteLLM endpoint or API-key caller values
