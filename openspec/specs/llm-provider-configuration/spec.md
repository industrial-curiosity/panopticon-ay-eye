# LLM provider configuration

## Purpose

Define how Panopticon instances select, validate, persist, and communicate
trusted LLM provider
configuration without storing credential values.

## Requirements

### Requirement: Template instances require explicit provider configuration

The template SHALL ship `panopticon.config.json` without a selected LLM
provider. Any child bootstrap or
provider-dependent CI path that reads an instance with no selected provider MUST
fail loudly before
performing provider-dependent work and MUST direct the maintainer to choose and
run one of the instance's
provider-specific Configure Panopticon workflows. General consumers of unrelated
org configuration,
including template sync, SHALL remain able to load an otherwise valid
unconfigured file.

#### Scenario: New instance has no implicit provider

- **WHEN** an instance is created directly from the template
- **THEN** its org configuration contains no selected LLM provider and does not
  silently default to
  LiteLLM, Bedrock, or any other provider

#### Scenario: Provider-dependent operation uses unconfigured instance

- **WHEN** child bootstrap or provider-dependent CI resolves an instance whose
  provider is unset
- **THEN** it exits non-zero before provider-dependent work and identifies both
  provider-specific
  configuration workflows as the available instance-bootstrap paths

### Requirement: Instance configuration workflow persists names, never credentials

The template SHALL provide `.github/workflows/configure-panopticon-litellm.yml`,
`.github/workflows/configure-panopticon-openai.yml`, and
`.github/workflows/configure-panopticon-bedrock.yml` as separate manual
`workflow_dispatch` interfaces.
Each workflow SHALL fix its provider identity without accepting a provider
selector and SHALL expose only
the independently optional provider-relevant GitHub Actions secret or variable
*name* inputs, plus the
common instance-token and request/job-budget name inputs, with documented
Panopticon names as logical
defaults. Each SHALL describe the instance checkout input as the name of an
organization secret containing
a GitHub token with instance-repository access and SHALL describe its
model-variable input with a concrete
provider-appropriate value example. Neither workflow SHALL accept, print, or
persist secret values. Each
SHALL validate every name and provider-specific requirement before
deterministically updating
`panopticon.config.json`, committing the change, and summarizing the org-level
values the maintainer must
configure. Every dispatch field SHALL identify whether it accepts a name or a
value, state its purpose, and
provide a concrete valid example whenever its accepted value is not obvious from
its label and default.

#### Scenario: Maintainer configures LiteLLM

- **WHEN** the maintainer opens and dispatches **Configure Panopticon —
  LiteLLM**
- **THEN** the form contains LiteLLM API-key, endpoint, model, instance-token,
  and common budget name inputs,
  contains no Bedrock credential-mode, AWS region, or role-ARN input, and
  commits a LiteLLM provider contract

#### Scenario: Maintainer configures OpenAI

- **WHEN** the maintainer opens and dispatches **Configure Panopticon — OpenAI**
- **THEN** the form contains OpenAI API-key, model, instance-token, and common
  budget name inputs; contains no endpoint, LiteLLM proxy, Bedrock
  credential-mode, AWS region, or role-ARN input; and commits an OpenAI provider
  contract with the fixed `https://api.openai.com/v1` endpoint

#### Scenario: Maintainer configures Bedrock

- **WHEN** the maintainer opens and dispatches **Configure Panopticon —
  Bedrock**
- **THEN** the form contains Bedrock credential-mode, model, instance-token,
  AWS, and common budget name
  inputs, contains no LiteLLM API-key or endpoint input, and commits a Bedrock
  provider contract

#### Scenario: Provider identity cannot be redirected

- **WHEN** a maintainer dispatches either provider-specific configuration
  workflow
- **THEN** the workflow passes its provider as a fixed trusted value and offers
  no input that can select a
  different provider, workflow path, action path, or repository

#### Scenario: Maintainer reviews clear optional name inputs

- **WHEN** the maintainer opens either provider-specific configuration workflow
- **THEN** it presents separate optional inputs for the request timeout,
  transport-attempt,
  correction-attempt, and job-timeout variable names, each prefilled with its
  documented default rather
  than requiring a JSON object, and it identifies the instance-token field as a
  GitHub token secret with
  instance-repository access

#### Scenario: Maintainer sees a provider-specific model example

- **WHEN** the maintainer reviews the model-variable-name input in either
  workflow
- **THEN** the workflow explains that the input is the organization variable's
  name and gives a concrete
  LiteLLM or Bedrock value example matching that workflow

#### Scenario: Maintainer chooses Bedrock authentication

- **WHEN** the maintainer opens **Configure Panopticon — Bedrock**
- **THEN** the workflow presents clearly labelled choices for a GitHub OIDC role
  and an instance-managed
  credential action, explaining the configuration each choice requires

#### Scenario: Input contains a secret value instead of a name

- **WHEN** a configured name is blank, malformed, or does not satisfy the
  accepted GitHub Actions
  identifier rules
- **THEN** the selected workflow rejects the input before writing or logging it
  as configuration

### Requirement: Configuration workflow failures have actionable summaries

Each provider-specific Configure Panopticon workflow SHALL write the detected
validation or persistence
failure reason and the corrective action to the GitHub Actions step summary
before it exits non-zero. Its
concise workflow annotation SHALL direct the maintainer to that summary. The
summary SHALL identify the
fixed provider and SHALL not expose credential values.

#### Scenario: Invalid provider-specific configuration input

- **WHEN** a maintainer dispatches either configuration workflow with an invalid
  configured name
- **THEN** the workflow exits non-zero without changing
  `panopticon.config.json`, and its step summary
  identifies the provider and invalid input and instructs the maintainer to
  correct the dispatch values and
  rerun

### Requirement: Configuration workflow imports checked-out tooling

Each provider-specific configuration workflow SHALL check out the instance
before invoking the shared local
configuration action. The action SHALL expose the checked-out workspace on its
Python import path before
importing Panopticon configuration modules, so validation and persistence run
against the checked-out
implementation on a clean GitHub Actions runner.

#### Scenario: Clean runner imports the configuration module

- **GIVEN** either workflow has checked out an instance repository containing
  the shared local action and
  Panopticon package
- **WHEN** the local configuration action starts on a clean runner
- **THEN** its Python process imports `panopticon.configure_instance`
  successfully before validating the
  dispatch inputs

### Requirement: Provider contracts select separate reusable workflows

The provider registry SHALL map each supported provider to a template-owned
reusable PR workflow and
its logical secret, variable, input, dependency, and permission contract.
LiteLLM, OpenAI, and Bedrock SHALL be separate reusable workflows. The
configuration file SHALL store the provider
identifier and configurable
names but SHALL NOT accept an arbitrary workflow path; child bootstrap SHALL
derive the workflow path
from the trusted registry.

#### Scenario: OpenAI provider selected

- **WHEN** child bootstrap resolves a valid `openai` provider contract
- **THEN** it selects the template-defined OpenAI reusable PR workflow and
  cannot be redirected to an arbitrary workflow path by org configuration

#### Scenario: Bedrock provider selected

- **WHEN** child bootstrap resolves a valid `bedrock` provider contract
- **THEN** it selects the template-defined Bedrock reusable PR workflow and
  cannot be redirected to an
  arbitrary workflow path by org configuration

#### Scenario: Unknown provider configured

- **WHEN** `panopticon.config.json` contains a provider identifier absent from
  the registry
- **THEN** provider validation fails loudly, names the unknown value and
  supported providers, and writes
  no child workflow

### Requirement: Bedrock evaluation has no LiteLLM caller dependency

The Bedrock reusable PR-evaluation workflow SHALL use only its declared
Bedrock provider contract for caller inputs and secrets. It SHALL NOT reference
LiteLLM API-key or endpoint caller configuration.

#### Scenario: Bedrock caller supplies its declared contract

- **WHEN** a child caller invokes the Bedrock reusable PR-evaluation workflow
  with the configured Bedrock credential mode, model, instance token, and
  budget values
- **THEN** GitHub Actions accepts the reusable-workflow contract and creates
  the evaluation job without requiring a LiteLLM API-key or endpoint value

### Requirement: Bedrock authentication supports trusted organization choices

The Bedrock provider contract SHALL persist one selected credential mode from a
closed registry. In
`github-oidc` mode, it SHALL require an AWS region variable and an AWS IAM
role-ARN variable, and the
configuration interface SHALL explain that the role is assumed through GitHub
OIDC and is not a Bedrock
model or inference-profile ARN. In `instance-managed` mode, it SHALL require
neither variable and SHALL
invoke only the fixed instance-local credential action
`.github/actions/panopticon-aws-credentials/action.yml`. That action SHALL
provide temporary AWS
credentials and the canonical Bedrock region environment before provider
preflight. Configuration SHALL
not select an arbitrary action path.

#### Scenario: Organization uses a GitHub OIDC role

- **WHEN** an organization selects `github-oidc` for Bedrock
- **THEN** it configures an AWS region such as `us-east-1` and an IAM role ARN
  such as
  `arn:aws:iam::123456789012:role/panopticon-bedrock`, and the provider workflow
  assumes that role through
  GitHub OIDC

#### Scenario: Organization manages credentials in its instance

- **WHEN** an organization selects `instance-managed` for Bedrock and provides
  the fixed credential action
- **THEN** its provider workflow invokes that action without requiring an
  org-level AWS region or role-ARN
  variable

#### Scenario: Instance-managed credential action is absent

- **WHEN** an organization selects `instance-managed` but its instance lacks the
  fixed credential action
- **THEN** bootstrap or provider evaluation fails before LLM work and names the
  required action path

#### Scenario: Configuration attempts to override the credential action

- **WHEN** instance configuration supplies an action path or other
  credential-action override
- **THEN** provider validation rejects the configuration before child bootstrap
  writes a workflow

### Requirement: Provider contracts declare effective value sources

The trusted provider registry SHALL declare which selected-provider variable
logical names are optional and which have template workflow defaults. Optional
names SHALL be a subset of the selected provider and credential mode's
registered variables. The instance contract MAY declare non-secret defaults
only for optional names. The instance token, provider credentials, API keys,
and authentication settings SHALL remain required and SHALL NOT be supplied by
an instance default or default-resolver action.

For each optional variable, the effective value SHALL be selected in this order:
an explicit non-empty organization Actions variable, a non-empty output from
the fixed instance default-resolver action, a non-empty non-secret instance
configuration default, then the declared non-empty template workflow default.
If no source supplies a value, provider configuration SHALL fail before
provider preflight or LLM work.

`job_timeout_minutes` SHALL be resolved in the generated caller because GitHub
evaluates job timeout before an instance action can run. Its supported order is
an explicit organization Actions variable, a non-secret instance configuration
default embedded in the generated caller, then the declared template workflow
default. The fixed instance default-resolver action SHALL NOT provide this
value.

#### Scenario: Organization Actions variable has precedence

- **GIVEN** an optional provider variable has values from all four trusted
  sources
- **WHEN** the provider workflow resolves its effective configuration
- **THEN** it uses the organization Actions variable and reports only that
  source label

#### Scenario: Fixed action supplies an absent optional value

- **GIVEN** an optional provider variable is absent from organization Actions
  variables and the fixed instance action returns a non-empty declared output
- **WHEN** the provider workflow resolves its effective configuration
- **THEN** it uses the action output before any instance-configured or workflow
  default

#### Scenario: Caller carries an instance job-timeout default

- **GIVEN** `job_timeout_minutes` is absent from organization Actions variables
  and the instance configuration declares a valid non-secret default
- **WHEN** child bootstrap generates a caller
- **THEN** the caller supplies that default to the reusable workflow before job
  timeout is evaluated and does not invoke the fixed action for it

#### Scenario: Optional value has no effective source

- **GIVEN** an optional provider variable is absent from every permitted source
- **WHEN** the provider workflow resolves its effective configuration
- **THEN** it fails before provider preflight, names the logical value and
  checked sources, and does not display any credential or value

#### Scenario: Invalid optional logical name is rejected

- **WHEN** an instance configuration marks an unregistered or required logical
  name optional or provides it with a default
- **THEN** provider-contract validation fails before writing configuration or
  generating a child caller

### Requirement: Integrator guidance explains effective provider configuration

Provider setup documentation and configuration workflow summaries SHALL present
an organization integrator with a provider-specific table that identifies every
logical value's purpose, required or optional status, allowed source(s) in
precedence order, configured Actions name when applicable, and a concrete next
action. The guide SHALL give an ordered setup path for the organization-variable
only case and a separate, clearly labelled path for the fixed instance default
resolver. It SHALL state that neither path accepts, stores, or displays
credential values.

#### Scenario: Integrator configures a provider with only organization values

- **WHEN** an integrator follows the provider setup guide without an instance
  default or default-resolver action
- **THEN** the guide identifies the required Actions names, verification
  command, expected result, and child-bootstrap command without requiring
  knowledge of implementation source

#### Scenario: Integrator needs dynamic optional defaults

- **WHEN** an integrator chooses the fixed instance default-resolver action
- **THEN** the guide names its fixed path, declared outputs, precedence, safe
  validation command, and recovery for a missing or invalid output without
  exposing credential values

### Requirement: Provider configuration has a deterministic revision

The effective provider contract SHALL have a deterministic revision derived from
all caller-relevant configured names, provider identity, credential mode,
permissions, workflow path, optionality declarations, instance defaults,
template defaults, and fixed default-resolver-action contract. Generated child
callers SHALL record and reusable workflows SHALL compare this revision before
provider-dependent work so an old caller cannot silently use a changed provider
configuration.

#### Scenario: Provider configuration changes after child bootstrap

- **WHEN** an instance changes a configured provider name, credential mode,
  optionality declaration, default source, or default-resolver-action contract
- **THEN** an existing child invokes a caller with its previous revision
- **THEN** the reusable workflow fails before provider work and prints the
  child-bootstrap recovery command

#### Scenario: Provider configuration is unchanged

- **WHEN** the generated caller revision matches the effective live instance
  contract
- **THEN** the reusable workflow proceeds with provider preflight

### Requirement: Unconfigured-instance remediation supports console and CLI paths

Every unconfigured-provider failure intended for a maintainer SHALL print direct
GitHub Actions console URLs for the resolved instance's LiteLLM, OpenAI, and
Bedrock configuration workflows and an
equivalent copy/paste
`gh workflow run` command for each using the resolved instance slug and default
branch. It SHALL explain
that the maintainer must choose exactly one provider path, then print an exact
one-line public installer
command with `PANOPTICON_INSTANCE` applied directly to the Python process,
without requiring a preceding
`export`.

#### Scenario: Bootstrap reports an unconfigured private instance

- **WHEN** child bootstrap resolves `acme/panopticon-instance` on default branch
  `main` with no provider
- **THEN** its remediation includes direct URLs ending in
  `configure-panopticon-litellm.yml` and
  `configure-panopticon-bedrock.yml`, corresponding `gh workflow run` commands
  for both files, ordered
  provider-choice instructions, and
  `curl -fsSL
  https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py
  | PANOPTICON_INSTANCE='acme/panopticon-instance' python3`

### Requirement: Provider configuration workflows share one mutation path

Both provider-specific configuration workflows SHALL invoke the same checked-in
local composite action for
provider validation, deterministic persistence, success and failure summaries,
no-op detection, and commit
and push behavior. Both workflows SHALL grant only the repository contents
permission required for that
action and SHALL use one shared concurrency group that prevents simultaneous
configuration mutation.

#### Scenario: Configuration behavior remains in parity

- **WHEN** structural workflow tests inspect both provider-specific callers
- **THEN** each checks out the instance, passes a fixed provider and only its
  relevant names to the same
  local action, grants `contents: write`, and uses the same configuration
  concurrency group

#### Scenario: Concurrent provider dispatches

- **WHEN** LiteLLM and Bedrock configuration runs are dispatched against the
  same instance branch at nearly
  the same time
- **THEN** GitHub Actions allows at most one configuration mutation to run at
  once rather than letting both
  build commits from the same instance state
