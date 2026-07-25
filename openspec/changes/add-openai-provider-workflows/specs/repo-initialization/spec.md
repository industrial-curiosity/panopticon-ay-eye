# Repository initialization OpenAI provider delta

## MODIFIED Requirements

### Requirement: Child bootstrap generates only the selected provider caller

The child SHALL retain a stable local `.github/workflows/panopticon-pr.yml`
caller. Bootstrap SHALL point that caller at only the provider workflow selected
by live instance configuration and SHALL emit explicit canonical input and
secret mappings from the configured org-level names, the exact permissions
required by that provider workflow, the selected trusted credential mode, and
the effective configuration revision. It SHALL map AWS region and role-ARN
variables only for Bedrock `github-oidc` mode. It SHALL NOT copy unselected
provider workflows into the child or use blanket `secrets: inherit`.

#### Scenario: OpenAI child caller generated

- **WHEN** the instance selects OpenAI and child bootstrap succeeds
- **THEN** the local PR caller references only the instance's OpenAI reusable
  workflow, omits LiteLLM-proxy and Bedrock-only setup, maps the configured
  model, API-key, and budget names explicitly, and exposes no endpoint mapping
  because the reusable workflow uses `https://api.openai.com/v1`

#### Scenario: Bedrock child caller generated

- **WHEN** the instance selects Bedrock and child bootstrap succeeds
- **THEN** the local PR caller references the instance's Bedrock reusable
  workflow, grants `id-token: write`, maps the configured instance-token secret
  and Bedrock variables explicitly, and includes the config revision

#### Scenario: LiteLLM child caller generated

- **WHEN** the instance selects LiteLLM and child bootstrap succeeds
- **THEN** the local PR caller references only the instance's LiteLLM workflow,
  omits Bedrock-only setup, and maps the configured endpoint, model, API-key,
  and budget names explicitly

#### Scenario: Instance-managed Bedrock child caller generated

- **WHEN** the instance selects Bedrock `instance-managed` credentials and child
  bootstrap succeeds
- **THEN** the local caller records that credential mode, maps no AWS region or
  role-ARN variable, and delegates credentials to the instance workflow

### Requirement: GitHub API rate-limit retries use bounded waits

The public launcher, bootstrap script, and local sync command SHALL cap every
GitHub API retry delay at 60 seconds. For a recognized rate limit, a valid
`Retry-After` value or future `X-RateLimit-Reset` timestamp SHALL determine the
requested delay, but the client SHALL wait no longer than 60 seconds before its
next retry. If neither value is usable, the client SHALL use its normal
exponential backoff, also capped at 60 seconds. Each rate-limit progress message
SHALL report the bounded wait duration without exposing a token or response body.

#### Scenario: Distant rate-limit reset is capped

- **GIVEN** a GitHub API response identifies a rate limit and its reset time is
  more than 60 seconds in the future
- **WHEN** the launcher, bootstrap, or sync client retries the request
- **THEN** it reports a wait of 60 seconds, waits no longer than 60 seconds, and
  retries within its existing retry budget

#### Scenario: Oversized Retry-After is capped

- **GIVEN** a GitHub API rate-limit response supplies a `Retry-After` value
  greater than 60 seconds
- **WHEN** the client retries the request
- **THEN** it waits and reports 60 seconds rather than the unbounded value

## ADDED Requirements

### Requirement: Setup guide stays focused on project configuration

The setup guide SHALL give maintainers the provider-selection steps and the
required secret and variable values needed to configure an instance. It SHALL
omit implementation and operational-tuning details that do not affect that
configuration, including request timeout behavior, retry attempts, retry
backoff, and job-budget calculations.

#### Scenario: Maintainer configures an instance without runtime tuning details

- **WHEN** a maintainer follows the setup guide to configure a provider
- **THEN** the guide identifies the provider workflow, required credentials, and
  required configuration values without describing request timeout, retry, or
  job-budget behavior
