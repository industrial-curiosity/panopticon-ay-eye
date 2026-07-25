# Design: GitHub API rate-limit retries

## Context

The public launcher, bootstrap installer, and local sync command each fetch
GitHub API resources. Bootstrap and sync currently retry `429`, gateway errors,
and connection failures, but GitHub commonly signals a primary API rate limit as
HTTP `403` with `X-RateLimit-Remaining: 0` and `X-RateLimit-Reset`. The public
launcher does not retry GitHub errors at all.

## Goals / Non-Goals

**Goals:**

- Recover automatically from GitHub-recognized primary and secondary rate
  limits without masking genuine authorization failures.
- Use GitHub’s requested delay when available and give users concise progress.
- Keep launcher, bootstrap, and sync behavior aligned without adding a runtime
  dependency.

**Non-Goals:**

- Bypass GitHub limits or replace authentication as the preferred path.
- Retry arbitrary `403` responses, malformed responses, or missing resources.
- Introduce a background downloader, persistent retry queue, or new
  configuration file.

## Decisions

### Classify rate limits from GitHub evidence

Treat `429` as retryable. Treat `403` as retryable only when `Retry-After` is
present, `X-RateLimit-Remaining` is `0`, or GitHub’s response says the rate
limit was exceeded. All other `401`, `403`, and `404` responses remain
immediate failures. This avoids turning a missing token or repository
permission into a misleading wait.

### Derive the retry delay from response headers

Use `Retry-After` first. Otherwise, for a valid `X-RateLimit-Reset` Unix epoch,
wait until that time, with a minimal positive delay. Fall back to existing
exponential backoff only when the response is recognized as rate-limited but
does not provide a usable delay. The implementation will inject time and sleep
dependencies for deterministic tests.

### Preserve client-specific boundaries

`install.py` keeps its redacted public-launcher error surface. Bootstrap and
sync retain mirrored local helpers because sync is vendored into child
repositories and cannot import bootstrap. Each client prints a short retry
message that names the wait duration but never the token or response body.

## Risks / Trade-offs

- [A false-positive `403` classification waits unnecessarily] → Require a
  GitHub rate-limit header or explicit rate-limit message before retrying.
- [A reset time is far away] → State the delay clearly so the user can choose
  to authenticate and rerun instead of assuming the installer has hung.
- [Mirrored bootstrap/sync implementations drift] → Add equivalent tests and
  retain the existing self-containment checks.

## Migration Plan

1. Release the updated public launcher and instance tooling.
2. Existing child repositories receive the sync recovery behavior on their next
   successful bootstrap or `python3 -m panopticon.sync` update.
3. No user data or configuration migration is required; a token remains the
   fastest way to avoid anonymous limits.

## Open Questions

None.
