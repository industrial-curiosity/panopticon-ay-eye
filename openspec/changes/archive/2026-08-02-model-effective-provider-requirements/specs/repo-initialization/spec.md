# Repo Initialization Delta

## MODIFIED Requirements

### Requirement: Org-level CI prerequisites

The init tooling SHALL derive required organization-level Actions secrets and
variables from the validated instance provider contract, including the
configured instance-token name, provider credentials, required model and
endpoint values, selected credential-mode settings, and bounded request/job
budget names that lack an effective trusted default. Optional values with an
effective workflow, instance-configured, or fixed-action source SHALL be
reported as supplied rather than missing. Child repos MUST NOT require per-repo
secret or variable configuration; generated callers SHALL map organization-level
names explicitly to canonical provider workflow inputs and secrets. Missing
values SHALL NOT block documentation or index initialization, but provider
configuration itself MUST be valid before bootstrap writes any child artifact.

Verifying org-level secrets and variables requires a GitHub auth token with
permission to read org-level Actions secrets and variables. With a resolved
`GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`, tooling SHALL query the org APIs
and report every missing required provider-resolved name and its kind. Without
such a token, tooling SHALL report no auth error and SHALL print the visible org
Actions settings URL plus equivalent `gh secret list --org` and `gh variable
list --org` commands, listing each required name and each optional value's
effective source. Every report SHALL distinguish `required`, `supplied by
default`, and `unresolved`, state the value's logical purpose, and give one
concise next action without printing its value.

#### Scenario: Configured instance token is missing

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization checks an org missing the instance-token secret name
  recorded by the instance
- **THEN** it reports that exact org-level secret name and how to configure it

#### Scenario: Configured required provider variable is missing

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization checks an org missing a variable required by the
  selected provider contract with no effective default
- **THEN** it reports that exact variable name, its provider purpose, and the
  organization configuration action

#### Scenario: Optional provider variable has a trusted default

- **WHEN** initialization checks an optional provider variable supplied by the
  fixed action, instance configuration, or template workflow
- **THEN** it reports the value as supplied with its source label and does not
  report an absent organization variable as a missing prerequisite

#### Scenario: Instance-managed credentials need no AWS variables

- **WHEN** initialization checks an instance using Bedrock `instance-managed`
  credentials
- **THEN** it does not report an AWS region or role-ARN variable as a missing
  prerequisite

#### Scenario: Auth token available

- **GIVEN** a GitHub auth token is resolved from `GH_TOKEN`, `GITHUB_TOKEN`, or
  `gh auth token`
- **WHEN** the org-level prerequisite check runs
- **THEN** it queries the org APIs and reports required missing names and
  effective optional sources separately

#### Scenario: No auth token available

- **GIVEN** no GitHub auth token can be resolved
- **WHEN** the org-level prerequisite check runs
- **THEN** it prints the visible web UI URL, equivalent listing commands, every
  required provider-resolved secret and variable name, and the source status of
  optional values without treating the missing auth token as an initialization
  failure
