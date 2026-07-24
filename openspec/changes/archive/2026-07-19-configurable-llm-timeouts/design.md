# Configurable LLM timeouts design

## Context

`LLMClient` currently fixes its per-request timeout at 60 seconds and retries
transport failures three times. Structured checks also allow two correction
requests, so one unhealthy check can occupy a runner for over nine minutes. The
reusable PR workflow has no explicit job budget. Organizations use different
LiteLLM-compatible models and proxies, so one fixed threshold cannot balance
healthy slow inference against fast failure everywhere.

## Goals / Non-Goals

## Goals

- Let an organization set bounded, non-secret CI timeout and retry values with
  GitHub Actions variables.
- Retain safe defaults: 90 seconds per request, two transport attempts, two
  JSON-correction retries, and a 20-minute workflow job budget.
- Validate runtime values before a request is sent and give actionable errors
  for invalid client settings.
- Keep the HTTP request shape and provider abstraction unchanged.

## Non-Goals

- Configure the LiteLLM proxy or any upstream provider timeout.
- Add provider SDKs, streaming, concurrency, or unlimited retries.
- Apply these values to local agent-harness flows or unrelated GitHub/network
  clients.

## Decisions

### Use four org-level Actions variables

The instance workflow will read `PANOPTICON_LLM_TIMEOUT_SECONDS`,
`PANOPTICON_LLM_MAX_ATTEMPTS`, `PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS`, and
`PANOPTICON_LLM_JOB_TIMEOUT_MINUTES`. Missing values use the stated defaults,
preserving existing installations without a migration.

The first three are read by `LLMClient.from_env`; the job value is evaluated
directly by GitHub Actions as `fromJSON(vars.PANOPTICON_LLM_JOB_TIMEOUT_MINUTES
|| '20')` in `jobs.evaluate.timeout-minutes`. GitHub supports expressions and the `vars` context at a job timeout field, and `fromJSON` converts the variable from text to an integer. This makes the outer guardrail effective before runner steps begin.

An instance administrator must configure a proxy timeout slightly above the
request timeout. That proxy setting remains outside Panopticon because endpoint
implementations differ.

### Strictly parse and bound client values

The Python runtime will parse the three request-level variables as base-10
integers and reject blank, non-integer, or out-of-range values before making a
request. Proposed bounds are 30–300 seconds, 1–3 transport attempts, and 0–2
correction retries. The bounds preserve a finite failure budget while
accommodating slower models.

The workflow-level variable cannot receive the same runtime validation because
GitHub evaluates job configuration before any step runs. Its documented range
will be 10–60 minutes; an invalid value fails GitHub Actions configuration
before execution rather than being silently ignored.

### Preserve independent checks and existing retry semantics

The LLM client continues to retry only transient HTTP and connection/time-out
errors, with exponential backoff. JSON correction remains separate from
transport retries. With defaults, one structured check is capped at six requests
and roughly 543 seconds; the 20-minute job timeout remains an outer fail-safe
for the two sequential LLM checks and all deterministic work.

Alternative: expose one combined total-request limit. Rejected because request
timeout, transient transport retries, and malformed-response correction
represent different failure modes and operators need to tune them independently.

Alternative: put the values in `panopticon.config.json`. Rejected because
`timeout-minutes` must be resolved before the runner can check out the instance
configuration.

## Risks / Trade-offs

- Invalid job timeout values fail before custom diagnostics → Document the exact
  variable, integer format, default, and allowed range.
- Higher values increase runner consumption during an outage → Keep finite upper
  bounds and an explicit job guardrail.
- A proxy timeout below the client timeout masks the client’s error handling →
  Document that the proxy threshold must be slightly higher.
- Configuration variables can be overridden at repository scope → Document that
  the reusable workflow resolves variables from the calling child repository and
  require consistent organization/repository configuration.

## Migration Plan

1. Release the workflow and runtime with defaults so existing organizations
   retain working behavior without variables.
2. Add the four variables at organization scope for organizations that need
   overrides.
3. Set LiteLLM’s own timeout a little above `PANOPTICON_LLM_TIMEOUT_SECONDS`.
4. Roll back by removing override variables; defaults resume on the next
   workflow run.

## Open Questions

None. The proposed defaults and configuration scope follow the requested timeout
policy.
