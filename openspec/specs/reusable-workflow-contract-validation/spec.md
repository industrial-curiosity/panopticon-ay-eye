# Reusable Workflow Contract Validation

## Purpose

Define deterministic validation of caller inputs and secrets in Panopticon's
provider-specific reusable GitHub Actions workflows.

## Requirements

### Requirement: Provider reusable workflows have validated caller contracts

The template SHALL deterministically discover and validate every shipped
reusable workflow that declares a root-level `on.workflow_call` contract,
including the LiteLLM, OpenAI, and Bedrock reusable PR workflows. The
validation SHALL report every dot-form `inputs.<name>` or
`secrets.<name>` expression reference that lacks a declaration in the matching
`workflow_call.inputs` or `workflow_call.secrets` mapping, and SHALL not
require a third-party YAML parser or GitHub-hosted service.

Repository-owned credential-free CI SHALL run this discovery-based validation
and the full Python test suite for pull requests, pushes, and manual dispatch.

#### Scenario: Shipped reusable workflow has a complete contract

- **WHEN** repository validation examines any shipped reusable workflow whose
  input and secret references are declared
- **THEN** it reports no contract errors

#### Scenario: Reusable workflow references an undeclared caller value

- **WHEN** repository validation examines a reusable workflow containing
  `inputs.endpoint` or `secrets.api_key` without the matching declaration
- **THEN** it reports that undeclared reference as a contract error before
  release

#### Scenario: New reusable workflow is discovered without a code list update

- **GIVEN** a shipped workflow newly declares a root-level `on.workflow_call`
  contract
- **WHEN** repository validation runs against the workflow directory
- **THEN** it validates that workflow without requiring a hardcoded filename
  update

#### Scenario: Repository CI enforces contract validation

- **WHEN** a pull request, push, or manual template-validation run starts
- **THEN** the credential-free workflow validates every discovered reusable
  workflow and runs the full Python test suite before succeeding

#### Scenario: Bedrock workflow is isolated from LiteLLM caller configuration

- **WHEN** repository validation examines the Bedrock reusable PR workflow
- **THEN** it finds no reference to LiteLLM endpoint or API-key caller values
