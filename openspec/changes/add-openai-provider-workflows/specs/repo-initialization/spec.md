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

### Requirement: GitHub API rate-limit retries honor GitHub-directed waits

The public launcher, bootstrap script, and local sync command SHALL honor a
valid GitHub `Retry-After` value for a recognized rate limit. When `Retry-After`
is absent and `X-RateLimit-Reset` supplies a future timestamp, they SHALL wait
until that reset time. They SHALL NOT cap either GitHub-directed delay. If
neither value is usable, they SHALL use their normal exponential backoff.
Each rate-limit progress message SHALL report the actual wait duration without
exposing a token or response body.

#### Scenario: Distant primary-limit reset is honored

- **GIVEN** a GitHub API response identifies a rate limit and its reset time is
  more than 60 seconds in the future
- **WHEN** the launcher, bootstrap, or sync client retries the request
- **THEN** it reports and waits until the supplied reset time before retrying

#### Scenario: Long secondary-limit Retry-After is honored

- **GIVEN** a GitHub API rate-limit response supplies a `Retry-After` value
  greater than 60 seconds
- **WHEN** the client retries the request
- **THEN** it reports and waits for the supplied duration before retrying

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

### Requirement: Installation guidance recommends GitHub authentication

The README and setup guide SHALL tell users to authenticate GitHub API requests
for every installation, including public instances, using `GH_TOKEN`,
`GITHUB_TOKEN`, or an existing `gh auth` session. They SHALL explain that
anonymous public-instance requests have a substantially lower GitHub API quota,
and SHALL direct users not to put token values directly in the launcher command.

#### Scenario: Public-instance user prepares a reliable install

- **GIVEN** a user is preparing to install a public instance repository
- **WHEN** the user follows the README or setup guide
- **THEN** the user sees that GitHub authentication is recommended to avoid the
  lower anonymous API quota and can choose a supported authentication source
