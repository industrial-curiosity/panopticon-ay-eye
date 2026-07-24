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
- **THEN** the Bedrock workflow obtains credentials through the selected trusted credential mode, installs
  its isolated dependency, preflights Converse, and then runs the same complete PR evaluation contract

### Requirement: Bedrock credential modes preserve the evaluation contract

The Bedrock reusable workflow SHALL obtain AWS credentials after checking out the instance and before
provider preflight. In `github-oidc` mode, it SHALL configure the selected AWS IAM role and region through
GitHub OIDC. In `instance-managed` mode, it SHALL invoke only the fixed checked-out instance action at
`.github/actions/panopticon-aws-credentials/action.yml`, which SHALL set temporary credentials and the
canonical Bedrock region environment. Both modes SHALL preserve the same evaluation, reporting, gating,
and branch-push behavior.

#### Scenario: Instance-managed credentials run provider evaluation

- **WHEN** a Bedrock instance selects `instance-managed` and its fixed credential action succeeds
- **THEN** provider preflight and the subsequent PR evaluation use the credentials and region it supplied

#### Scenario: Credential action cannot be redirected

- **WHEN** a provider configuration contains a credential-action path override
- **THEN** the workflow rejects the invalid contract before invoking any action or LLM work

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

### Requirement: Provider workflow failures have actionable summaries

Each provider-specific PR-evaluation workflow SHALL write the detected failure reason and a corrective
action to the GitHub Actions step summary before any explicit non-zero exit caused by invalid provider
configuration, a missing required credential action, or a failed branch-state index merge. Its concise
workflow annotation SHALL direct the maintainer to the summary.

#### Scenario: Bedrock credential action is unavailable

- **GIVEN** the instance selects `instance-managed` Bedrock credentials
- **WHEN** the checked-out instance lacks `.github/actions/panopticon-aws-credentials/action.yml`
- **THEN** the Bedrock workflow exits non-zero before provider preflight and its step summary identifies
  the required action path and the available credential-mode recovery

#### Scenario: Branch-state merge fails

- **WHEN** either provider workflow cannot merge the PR branch state into the instance branch
- **THEN** it exits non-zero and its step summary identifies the failed merge, its exit status, and the
  instruction to correct the reported index or configuration problem before rerunning
