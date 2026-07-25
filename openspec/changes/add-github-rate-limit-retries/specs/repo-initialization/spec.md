# Repo initialization delta: GitHub rate-limit retries

## MODIFIED Requirements

### Requirement: GitHub API request resilience

The public launcher, bootstrap script, and local sync command SHALL retry
transient GitHub API failures from their retrieval calls. They SHALL retry
`429`, `5xx`, and connection-level errors with exponential backoff before
giving up. They SHALL also retry a `403` only when GitHub identifies it as a
rate limit through `Retry-After`, `X-RateLimit-Remaining: 0`, or an explicit
rate-limit response message.

For a recognized rate limit, they SHALL use `Retry-After` when supplied. If it
is absent and `X-RateLimit-Reset` supplies a valid Unix timestamp, they SHALL
wait until that reset time. If neither delay is usable, they SHALL use the
normal exponential backoff. Before each rate-limit retry, they SHALL print a
concise message that identifies rate limiting and the wait duration without
including a token or response body.

All other `401`, `403`, and `404` responses SHALL fail immediately without a
retry. Once any retry budget is exhausted, bootstrap and sync SHALL retain
their actionable status-and-body failure detail; the public launcher SHALL
retain its redacted error surface. The launcher, bootstrap, and sync clients
MUST implement this behavior despite their separate import boundaries.

#### Scenario: Primary rate-limit response waits until reset and succeeds

- **GIVEN** a GitHub API call returns `403` with
  `X-RateLimit-Remaining: 0` and a future `X-RateLimit-Reset` value
- **WHEN** the launcher, bootstrap, or sync client makes that call
- **THEN** it reports the rate-limit wait, waits until the supplied reset time,
  and retries the request

#### Scenario: Secondary rate-limit response uses Retry-After

- **GIVEN** a GitHub API call returns a rate-limit response with `Retry-After`
- **WHEN** the client makes that call
- **THEN** it waits for that duration before retrying and does not expose the
  response body or a token in its progress message

#### Scenario: Recognized rate-limit fallback uses exponential backoff

- **GIVEN** a GitHub API call returns a recognized rate-limit response without
  a usable `Retry-After` or `X-RateLimit-Reset` value
- **WHEN** the client retries the request
- **THEN** it uses the same exponential-backoff policy as other transient
  failures

#### Scenario: Genuine forbidden response fails immediately

- **GIVEN** a GitHub API call returns `403` without rate-limit evidence
- **WHEN** the launcher, bootstrap, or sync client makes that call
- **THEN** it fails immediately without waiting or retrying so the user can
  correct token permissions or repository access

#### Scenario: Rate-limit retries are exhausted

- **GIVEN** recognized GitHub rate-limit responses persist through the client’s
  retry budget
- **WHEN** the client makes the request
- **THEN** it fails only after the configured retry attempts and preserves its
  existing safe failure format
