# LLM provider configuration delta

## ADDED Requirements

### Requirement: Template instances require explicit provider configuration

The template SHALL ship `panopticon.config.json` without a selected LLM provider. Any child
bootstrap or provider-dependent CI path that reads an instance with no selected provider MUST fail
loudly before performing provider-dependent work and MUST direct the maintainer to run the instance's
`Configure Panopticon` workflow. General consumers of unrelated org configuration, including template
sync, SHALL remain able to load an otherwise valid unconfigured file.

#### Scenario: New instance has no implicit provider

- **WHEN** an instance is created directly from the template
- **THEN** its org configuration contains no selected LLM provider and does not silently default to
  LiteLLM, Bedrock, or any other provider

#### Scenario: Provider-dependent operation uses unconfigured instance

- **WHEN** child bootstrap or provider-dependent CI resolves an instance whose provider is unset
- **THEN** it exits non-zero before provider-dependent work and identifies `Configure Panopticon` as
  the required instance-bootstrap workflow

### Requirement: Instance configuration workflow persists names, never credentials

The template SHALL provide `.github/workflows/configure-panopticon.yml` with a manual
`workflow_dispatch` interface. It SHALL require a deliberate provider choice from the supported provider
registry and SHALL accept one independently optional provider-relevant GitHub Actions secret or variable
*name* input for each configured name, with the documented Panopticon name as its logical default. It SHALL
describe the instance checkout input as the name of an organization secret containing a GitHub token and
state that the token needs access to the instance repository. It SHALL describe the model-variable input
with a concrete example of the variable's value appropriate to the selected provider. It MUST NOT accept,
print, or persist secret values. It SHALL validate every name and provider-specific requirement before
deterministically updating `panopticon.config.json`, committing the change, and summarizing the org-level
values the maintainer must configure.

#### Scenario: Maintainer configures Bedrock with default names

- **WHEN** the maintainer dispatches `Configure Panopticon`, selects `bedrock`, and accepts the
  provider's default secret and variable names
- **THEN** the workflow commits a Bedrock provider contract containing those names but no credential
  values

#### Scenario: Maintainer reviews clear optional name inputs

- **WHEN** the maintainer opens `Configure Panopticon`
- **THEN** it presents separate optional inputs for the request timeout, transport-attempt,
  correction-attempt, and job-timeout variable names, each prefilled with its documented default rather
  than requiring a JSON object, and it identifies the instance-token field as a GitHub token secret with
  instance-repository access

#### Scenario: Maintainer sees a model-value example

- **WHEN** the maintainer selects a provider and reviews the model-variable input
- **THEN** the workflow explains that the input is the organization variable's name and gives a concrete
  example of the value to store in that variable for the selected provider

#### Scenario: Maintainer leaves the provider sentinel selected

- **WHEN** the configuration workflow is dispatched without replacing its non-provider sentinel choice
- **THEN** it fails without changing `panopticon.config.json` and tells the maintainer to select a
  supported provider

#### Scenario: Input contains a secret value instead of a name

- **WHEN** a configured name is blank, malformed, or does not satisfy the accepted GitHub Actions
  identifier rules
- **THEN** the workflow rejects the input before writing or logging it as configuration

### Requirement: Provider contracts select separate reusable workflows

The provider registry SHALL map each supported provider to a template-owned reusable PR workflow and
its logical secret, variable, input, dependency, and permission contract. LiteLLM and Bedrock SHALL be
separate reusable workflows. The configuration file SHALL store the provider identifier and configurable
names but SHALL NOT accept an arbitrary workflow path; child bootstrap SHALL derive the workflow path
from the trusted registry.

#### Scenario: Bedrock provider selected

- **WHEN** child bootstrap resolves a valid `bedrock` provider contract
- **THEN** it selects the template-defined Bedrock reusable PR workflow and cannot be redirected to an
  arbitrary workflow path by org configuration

#### Scenario: Unknown provider configured

- **WHEN** `panopticon.config.json` contains a provider identifier absent from the registry
- **THEN** provider validation fails loudly, names the unknown value and supported providers, and writes
  no child workflow

### Requirement: Provider configuration has a deterministic revision

The effective provider contract SHALL have a deterministic revision derived from all caller-relevant
provider, secret-name, variable-name, workflow, and permission settings. Child callers SHALL record and
pass that revision. Provider workflows SHALL compare it with the live instance configuration and MUST
fail loudly when they differ rather than continuing under stale wiring.

#### Scenario: Secret name changes after child bootstrap

- **WHEN** an instance maintainer changes a configured secret name and an existing child invokes a caller
  generated from the prior revision
- **THEN** the provider workflow fails as stale and directs the user to rerun child bootstrap

#### Scenario: Provider configuration is unchanged

- **WHEN** the generated caller revision matches the effective live instance contract
- **THEN** provider evaluation proceeds normally

### Requirement: Unconfigured-instance remediation supports console and CLI paths

Every unconfigured-provider failure intended for a maintainer SHALL print both a direct GitHub Actions
console URL for the resolved instance's `Configure Panopticon` workflow and an equivalent copy/paste
`gh workflow run` command using the resolved instance slug and default branch. It SHALL then print an exact
one-line public installer command with `PANOPTICON_INSTANCE` applied directly to the Python process, without
requiring a preceding `export`.

#### Scenario: Bootstrap reports an unconfigured private instance

- **WHEN** child bootstrap resolves `acme/panopticon-instance` on default branch `main` with no provider
- **THEN** its remediation includes
  `https://github.com/acme/panopticon-instance/actions/workflows/configure-panopticon.yml`, a corresponding
  `gh workflow run` command, ordered console instructions, and
  `curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='acme/panopticon-instance' python3`
