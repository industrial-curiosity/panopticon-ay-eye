# LLM provider configuration delta

## MODIFIED Requirements

### Requirement: Template instances require explicit provider configuration

The template SHALL ship `panopticon.config.json` without a selected LLM provider. Any child bootstrap or
provider-dependent CI path that reads an instance with no selected provider MUST fail loudly before
performing provider-dependent work and MUST direct the maintainer to choose and run one of the instance's
provider-specific Configure Panopticon workflows. General consumers of unrelated org configuration,
including template sync, SHALL remain able to load an otherwise valid unconfigured file.

#### Scenario: New instance has no implicit provider

- **WHEN** an instance is created directly from the template
- **THEN** its org configuration contains no selected LLM provider and does not silently default to
  LiteLLM, Bedrock, or any other provider

#### Scenario: Provider-dependent operation uses unconfigured instance

- **WHEN** child bootstrap or provider-dependent CI resolves an instance whose provider is unset
- **THEN** it exits non-zero before provider-dependent work and identifies both provider-specific
  configuration workflows as the available instance-bootstrap paths

### Requirement: Instance configuration workflow persists names, never credentials

The template SHALL provide `.github/workflows/configure-panopticon-litellm.yml` and
`.github/workflows/configure-panopticon-bedrock.yml` as separate manual `workflow_dispatch` interfaces.
Each workflow SHALL fix its provider identity without accepting a provider selector and SHALL expose only
the independently optional provider-relevant GitHub Actions secret or variable *name* inputs, plus the
common instance-token and request/job-budget name inputs, with documented Panopticon names as logical
defaults. Each SHALL describe the instance checkout input as the name of an organization secret containing
a GitHub token with instance-repository access and SHALL describe its model-variable input with a concrete
provider-appropriate value example. Neither workflow SHALL accept, print, or persist secret values. Each
SHALL validate every name and provider-specific requirement before deterministically updating
`panopticon.config.json`, committing the change, and summarizing the org-level values the maintainer must
configure. Every dispatch field SHALL identify whether it accepts a name or a value, state its purpose, and
provide a concrete valid example whenever its accepted value is not obvious from its label and default.

#### Scenario: Maintainer configures LiteLLM

- **WHEN** the maintainer opens and dispatches **Configure Panopticon — LiteLLM**
- **THEN** the form contains LiteLLM API-key, endpoint, model, instance-token, and common budget name inputs,
  contains no Bedrock credential-mode, AWS region, or role-ARN input, and commits a LiteLLM provider contract

#### Scenario: Maintainer configures Bedrock

- **WHEN** the maintainer opens and dispatches **Configure Panopticon — Bedrock**
- **THEN** the form contains Bedrock credential-mode, model, instance-token, AWS, and common budget name
  inputs, contains no LiteLLM API-key or endpoint input, and commits a Bedrock provider contract

#### Scenario: Provider identity cannot be redirected

- **WHEN** a maintainer dispatches either provider-specific configuration workflow
- **THEN** the workflow passes its provider as a fixed trusted value and offers no input that can select a
  different provider, workflow path, action path, or repository

#### Scenario: Maintainer reviews clear optional name inputs

- **WHEN** the maintainer opens either provider-specific configuration workflow
- **THEN** it presents separate optional inputs for the request timeout, transport-attempt,
  correction-attempt, and job-timeout variable names, each prefilled with its documented default rather
  than requiring a JSON object, and it identifies the instance-token field as a GitHub token secret with
  instance-repository access

#### Scenario: Maintainer sees a provider-specific model example

- **WHEN** the maintainer reviews the model-variable-name input in either workflow
- **THEN** the workflow explains that the input is the organization variable's name and gives a concrete
  LiteLLM or Bedrock value example matching that workflow

#### Scenario: Maintainer chooses Bedrock authentication

- **WHEN** the maintainer opens **Configure Panopticon — Bedrock**
- **THEN** the workflow presents clearly labelled choices for a GitHub OIDC role and an instance-managed
  credential action, explaining the configuration each choice requires

#### Scenario: Input contains a secret value instead of a name

- **WHEN** a configured name is blank, malformed, or does not satisfy the accepted GitHub Actions
  identifier rules
- **THEN** the selected workflow rejects the input before writing or logging it as configuration

### Requirement: Configuration workflow failures have actionable summaries

Each provider-specific Configure Panopticon workflow SHALL write the detected validation or persistence
failure reason and the corrective action to the GitHub Actions step summary before it exits non-zero. Its
concise workflow annotation SHALL direct the maintainer to that summary. The summary SHALL identify the
fixed provider and SHALL not expose credential values.

#### Scenario: Invalid provider-specific configuration input

- **WHEN** a maintainer dispatches either configuration workflow with an invalid configured name
- **THEN** the workflow exits non-zero without changing `panopticon.config.json`, and its step summary
  identifies the provider and invalid input and instructs the maintainer to correct the dispatch values and
  rerun

### Requirement: Configuration workflow imports checked-out tooling

Each provider-specific configuration workflow SHALL check out the instance before invoking the shared local
configuration action. The action SHALL expose the checked-out workspace on its Python import path before
importing Panopticon configuration modules, so validation and persistence run against the checked-out
implementation on a clean GitHub Actions runner.

#### Scenario: Clean runner imports the configuration module

- **GIVEN** either workflow has checked out an instance repository containing the shared local action and
  Panopticon package
- **WHEN** the local configuration action starts on a clean runner
- **THEN** its Python process imports `panopticon.configure_instance` successfully before validating the
  dispatch inputs

### Requirement: Unconfigured-instance remediation supports console and CLI paths

Every unconfigured-provider failure intended for a maintainer SHALL print direct GitHub Actions console URLs
for the resolved instance's LiteLLM and Bedrock configuration workflows and an equivalent copy/paste
`gh workflow run` command for each using the resolved instance slug and default branch. It SHALL explain
that the maintainer must choose exactly one provider path, then print an exact one-line public installer
command with `PANOPTICON_INSTANCE` applied directly to the Python process, without requiring a preceding
`export`.

#### Scenario: Bootstrap reports an unconfigured private instance

- **WHEN** child bootstrap resolves `acme/panopticon-instance` on default branch `main` with no provider
- **THEN** its remediation includes direct URLs ending in `configure-panopticon-litellm.yml` and
  `configure-panopticon-bedrock.yml`, corresponding `gh workflow run` commands for both files, ordered
  provider-choice instructions, and
  `curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='acme/panopticon-instance' python3`

## ADDED Requirements

### Requirement: Provider configuration workflows share one mutation path

Both provider-specific configuration workflows SHALL invoke the same checked-in local composite action for
provider validation, deterministic persistence, success and failure summaries, no-op detection, and commit
and push behavior. Both workflows SHALL grant only the repository contents permission required for that
action and SHALL use one shared concurrency group that prevents simultaneous configuration mutation.

#### Scenario: Configuration behavior remains in parity

- **WHEN** structural workflow tests inspect both provider-specific callers
- **THEN** each checks out the instance, passes a fixed provider and only its relevant names to the same
  local action, grants `contents: write`, and uses the same configuration concurrency group

#### Scenario: Concurrent provider dispatches

- **WHEN** LiteLLM and Bedrock configuration runs are dispatched against the same instance branch at nearly
  the same time
- **THEN** GitHub Actions allows at most one configuration mutation to run at once rather than letting both
  build commits from the same instance state
