# LLM provider configuration OpenAI provider delta

## MODIFIED Requirements

### Requirement: Instance configuration workflow persists names, never credentials

The template SHALL provide `.github/workflows/configure-panopticon-litellm.yml`,
`.github/workflows/configure-panopticon-openai.yml`, and
`.github/workflows/configure-panopticon-bedrock.yml` as separate manual
`workflow_dispatch` interfaces. Each workflow SHALL fix its provider identity
without accepting a provider selector and SHALL expose only the independently
optional provider-relevant GitHub Actions secret or variable *name* inputs,
plus the common instance-token and request/job-budget name inputs, with
documented Panopticon names as logical defaults. Each SHALL describe the
instance checkout input as the name of an organization secret containing a
GitHub token with instance-repository access and SHALL describe its
model-variable input with a concrete provider-appropriate value example.
Neither workflow SHALL accept, print, or persist secret values. Each SHALL
validate every name and provider-specific requirement before deterministically
updating `panopticon.config.json`, committing the change, and summarizing the
org-level values the maintainer must configure. Every dispatch field SHALL
identify whether it accepts a name or a value, state its purpose, and provide a
concrete valid example whenever its accepted value is not obvious from its label
and default.

#### Scenario: Maintainer configures OpenAI

- **WHEN** the maintainer opens and dispatches **Configure Panopticon — OpenAI**
- **THEN** the form contains OpenAI API-key, model, instance-token, and common
  budget name inputs; contains no endpoint, LiteLLM proxy, Bedrock
  credential-mode, AWS region, or role-ARN input; and commits an OpenAI provider
  contract with the fixed `https://api.openai.com/v1` endpoint

#### Scenario: OpenAI endpoint cannot be configured

- **WHEN** a maintainer configures the OpenAI provider
- **THEN** the persisted contract contains no endpoint variable name and its
  workflow exposes no endpoint input or override

#### Scenario: Maintainer configures LiteLLM

- **WHEN** the maintainer opens and dispatches **Configure Panopticon —
  LiteLLM**
- **THEN** the form contains LiteLLM API-key, endpoint, model, instance-token,
  and common budget name inputs; contains no Bedrock credential-mode, AWS
  region, or role-ARN input; and commits a LiteLLM provider contract

#### Scenario: Maintainer configures Bedrock

- **WHEN** the maintainer opens and dispatches **Configure Panopticon —
  Bedrock**
- **THEN** the form contains Bedrock credential-mode, model, instance-token,
  AWS, and common budget name inputs; contains no LiteLLM or OpenAI API-key or
  endpoint input; and commits a Bedrock provider contract

#### Scenario: Provider identity cannot be redirected

- **WHEN** a maintainer dispatches any provider-specific configuration workflow
- **THEN** the workflow passes its provider as a fixed trusted value and offers
  no input that can select a different provider, workflow path, action path, or
  repository

#### Scenario: Maintainer reviews clear optional name inputs

- **WHEN** the maintainer opens any provider-specific configuration workflow
- **THEN** it presents separate optional inputs for the request timeout,
  transport-attempt, correction-attempt, and job-timeout variable names, each
  prefilled with its documented default rather than requiring a JSON object, and
  it identifies the instance-token field as a GitHub token secret with
  instance-repository access

#### Scenario: Maintainer sees a provider-specific model example

- **WHEN** the maintainer reviews the model-variable-name input in any workflow
- **THEN** the workflow explains that the input is the organization variable's
  name and gives a concrete LiteLLM, OpenAI, or Bedrock value example matching
  that workflow

#### Scenario: Maintainer chooses Bedrock authentication

- **WHEN** the maintainer opens **Configure Panopticon — Bedrock**
- **THEN** the workflow presents clearly labelled choices for a GitHub OIDC role
  and an instance-managed credential action, explaining the configuration each
  choice requires

#### Scenario: Input contains a secret value instead of a name

- **WHEN** a configured name is blank, malformed, or does not satisfy the
  accepted GitHub Actions identifier rules
- **THEN** the selected workflow rejects the input before writing or logging it
  as configuration

### Requirement: Provider contracts select separate reusable workflows

The provider registry SHALL map each supported provider to a template-owned
reusable PR workflow and its logical secret, variable, input, dependency, and
permission contract. LiteLLM, OpenAI, and Bedrock SHALL be separate reusable
workflows. The configuration file SHALL store the provider identifier and
configurable names but SHALL NOT accept an arbitrary workflow path; child
bootstrap SHALL derive the workflow path from the trusted registry.

#### Scenario: OpenAI provider selected

- **WHEN** child bootstrap resolves a valid `openai` provider contract
- **THEN** it selects the template-defined OpenAI reusable PR workflow and
  cannot be redirected to an arbitrary workflow path by org configuration

#### Scenario: Bedrock provider selected

- **WHEN** child bootstrap resolves a valid `bedrock` provider contract
- **THEN** it selects the template-defined Bedrock reusable PR workflow and
  cannot be redirected to an arbitrary workflow path by org configuration

#### Scenario: Unknown provider configured

- **WHEN** `panopticon.config.json` contains a provider identifier absent from
  the registry
- **THEN** provider validation fails loudly, names the unknown value and
  supported providers, and writes no child workflow

### Requirement: Unconfigured-instance remediation supports console and CLI paths

Every unconfigured-provider failure intended for a maintainer SHALL print
direct GitHub Actions console URLs for the resolved instance's LiteLLM, OpenAI,
and Bedrock configuration workflows and an equivalent copy/paste
`gh workflow run` command for each using the resolved instance slug and default
branch. It SHALL explain that the maintainer must choose exactly one provider
path, then print an exact one-line public installer command with
`PANOPTICON_INSTANCE` applied directly to the Python process, without requiring
a preceding `export`.

#### Scenario: Bootstrap reports an unconfigured private instance

- **WHEN** child bootstrap resolves `acme/panopticon-instance` on default branch
  `main` with no provider
- **THEN** its remediation includes direct URLs ending in
  `configure-panopticon-litellm.yml`, `configure-panopticon-openai.yml`, and
  `configure-panopticon-bedrock.yml`; corresponding `gh workflow run` commands
  for all three files; ordered provider-choice instructions; and
  `curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='acme/panopticon-instance' python3`
