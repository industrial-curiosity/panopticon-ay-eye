# PR evaluation delta

## MODIFIED Requirements

### Requirement: Bounded PR-evaluation job duration

Each provider-specific reusable PR-evaluation workflow SHALL set an explicit timeout for its evaluate job
from the canonical workflow input mapped by child bootstrap from the configured org-level job-timeout
variable name, using 20 minutes when the mapped value is unset. The setup guide SHALL document that the
value accepts a whole number from 10 through 60 and is evaluated by GitHub Actions before the job starts.

#### Scenario: Default evaluate-job duration

- **WHEN** a provider-specific PR workflow receives no mapped job-timeout value
- **THEN** GitHub Actions terminates the evaluate job after 20 minutes if it has not completed

#### Scenario: Configured evaluate-job duration

- **WHEN** child bootstrap maps a configured org variable whose value is a whole number from 10 through 60
- **THEN** the selected provider workflow uses that number as its evaluate job timeout in minutes

## ADDED Requirements

### Requirement: Separate provider workflows preserve the PR evaluation contract

The template SHALL ship independent LiteLLM and Bedrock reusable PR workflows. Each SHALL own its provider
setup, authentication, dependency installation, preflight, canonical inputs and secrets, and complete PR
evaluation job. Both workflows MUST preserve the existing initialization, independent-check execution,
reporting, gating, simulation, and branch-push contracts. Provider-independent merge and PR-close workflows
SHALL remain shared.

#### Scenario: LiteLLM PR evaluation

- **WHEN** a correctly wired LiteLLM child opens or updates a PR
- **THEN** the LiteLLM workflow runs the complete existing PR evaluation contract without AWS setup

#### Scenario: Bedrock PR evaluation

- **WHEN** a correctly wired Bedrock child opens or updates a PR
- **THEN** the Bedrock workflow first configures OIDC credentials and its isolated dependency, preflights
  Converse, and then runs the same complete PR evaluation contract

### Requirement: Legacy and stale callers fail with complete recovery instructions

The instance SHALL retain a legacy `panopticon-pr.yml` guard for callers generated before provider
selection and each provider workflow SHALL validate its configuration revision and canonical required
values before provider-dependent work. A legacy, stale, or empty renamed-secret path SHALL fail as an
operational error with a concise annotation and a detailed step summary. The summary SHALL state the cause,
show the resolved instance's direct `Configure Panopticon` Actions URL when configuration is required, give
ordered console instructions and an equivalent `gh workflow run` command, and give the exact one-line child
bootstrap command plus commit, push, and rerun instructions when caller regeneration is required.

#### Scenario: Legacy generic caller runs

- **WHEN** a child still references instance workflow `panopticon-pr.yml`
- **THEN** the guard fails after reading the child instance identity and prints complete configuration and
  child-bootstrap recovery commands rather than producing a workflow-load error

#### Scenario: Provider revision is stale

- **WHEN** a provider workflow receives a configuration revision different from the live instance contract
- **THEN** it fails before LLM checks and prints an exact installer command in the form
  `curl -fsSL <public-installer-url> | PANOPTICON_INSTANCE='<owner/repo>' python3`

