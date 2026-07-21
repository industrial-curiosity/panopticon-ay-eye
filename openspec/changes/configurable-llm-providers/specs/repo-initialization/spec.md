# Repository initialization delta

## ADDED Requirements

### Requirement: Child bootstrap validates provider configuration before writing

The child bootstrap installer SHALL fetch and strictly validate the instance's provider configuration
before selecting a skills location, downloading content, vendoring tooling, or writing workflows. It SHALL
distinguish an inaccessible config, malformed config, missing provider, unknown provider, invalid configured
name, and selected workflow absent at `workflow_ref`. Any such failure MUST leave all child files untouched.

#### Scenario: Instance provider is unset

- **WHEN** child bootstrap reads a valid instance config with no selected provider
- **THEN** it exits non-zero with console and CLI instance-configuration instructions and writes no child
  files

#### Scenario: Selected provider workflow is absent at the configured ref

- **WHEN** the instance config selects Bedrock but the selected `workflow_ref` lacks the registered Bedrock
  workflow
- **THEN** bootstrap fails before writing, names the missing path and ref, and explains how to select a ref
  containing the provider workflow

#### Scenario: Instance config cannot be fetched

- **WHEN** the GitHub API cannot retrieve `panopticon.config.json`
- **THEN** bootstrap reports the access or transport failure instead of treating it as empty configuration

### Requirement: Child bootstrap generates only the selected provider caller

The child SHALL retain a stable local `.github/workflows/panopticon-pr.yml` caller. Bootstrap SHALL point
that caller at only the provider workflow selected by live instance configuration and SHALL emit explicit
canonical input and secret mappings from the configured org-level names, the exact permissions required by
that provider workflow, the selected trusted credential mode, and the effective configuration revision. It
SHALL map AWS region and role-ARN variables only for Bedrock `github-oidc` mode. It SHALL NOT copy
unselected provider workflows into the child or use blanket `secrets: inherit`.

#### Scenario: Bedrock child caller generated

- **WHEN** the instance selects Bedrock and child bootstrap succeeds
- **THEN** the local PR caller references the instance's Bedrock reusable workflow, grants `id-token: write`,
  maps the configured instance-token secret and Bedrock variables explicitly, and includes the config
  revision

#### Scenario: LiteLLM child caller generated

- **WHEN** the instance selects LiteLLM and child bootstrap succeeds
- **THEN** the local PR caller references only the instance's LiteLLM workflow, omits Bedrock-only setup,
  and maps the configured endpoint, model, API-key, and budget names explicitly

#### Scenario: Instance-managed Bedrock child caller generated

- **WHEN** the instance selects Bedrock `instance-managed` credentials and child bootstrap succeeds
- **THEN** the local caller records that credential mode, maps no AWS region or role-ARN variable, and
  references the selected instance workflow only

### Requirement: Stale caller remediation prints an exact installer command

Every bootstrap or workflow failure caused by stale provider, secret-name, variable-name, or revision SHALL
explain the cause and print a copy/paste child-bootstrap command using the resolved instance
slug. The command SHALL set `PANOPTICON_INSTANCE` on the piped Python process itself, without an `export`,
and SHALL instruct the user to run it from inside the child clone, review and commit the generated changes,
push them, and rerun or await the PR workflow.

#### Scenario: Renamed instance-token secret leaves old caller empty

- **WHEN** an existing caller maps a removed old instance-token secret name and the reusable workflow
  receives an empty canonical token
- **THEN** it fails before instance checkout and prints the exact public-installer command for that child’s
  recorded instance plus the commit, push, and rerun instructions

## MODIFIED Requirements

### Requirement: Org-level CI prerequisites

The init tooling SHALL derive required org-level Actions secrets and variables from the validated instance
provider contract, including the configured instance-token name, provider credentials, model and endpoint
or selected credential-mode settings, and bounded request/job budget names. These values are consumed only
by shared CI workflows. Child repos MUST NOT require per-repo secret or variable configuration; generated
callers SHALL map org-level names explicitly to canonical provider workflow inputs and secrets. Missing
values SHALL NOT block documentation or index initialization, but provider configuration itself MUST be
valid before bootstrap writes any child artifact.

Verifying org-level secrets and variables requires a GitHub auth token with permission to read org-level
Actions secrets and variables. With a resolved `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`, tooling SHALL
query the org APIs and report every missing provider-resolved name and its kind. Without such a token,
tooling SHALL report no auth error and SHALL print the visible org Actions settings URL plus equivalent
`gh secret list --org` and `gh variable list --org` commands, listing every provider-resolved name to check.

#### Scenario: Configured instance token is missing

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization checks an org missing the instance-token secret name recorded by the instance
- **THEN** it reports that exact org-level secret name and how to configure it

#### Scenario: Configured provider variable is missing

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization checks an org missing a variable required by the selected provider contract
- **THEN** it reports that exact variable name and its provider purpose

#### Scenario: Instance-managed credentials need no AWS variables

- **WHEN** initialization checks an instance using Bedrock `instance-managed` credentials
- **THEN** it does not report an AWS region or role-ARN variable as a missing prerequisite

#### Scenario: Auth token available

- **GIVEN** a GitHub auth token is resolved from `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`
- **WHEN** the org-level prerequisite check runs
- **THEN** it queries the org APIs and reports exactly which provider-resolved names are absent

#### Scenario: No auth token available

- **GIVEN** no GitHub auth token can be resolved
- **WHEN** the org-level prerequisite check runs
- **THEN** it prints the visible web UI URL, equivalent listing commands, and every provider-resolved secret
  and variable name without treating the missing auth token as an initialization failure
