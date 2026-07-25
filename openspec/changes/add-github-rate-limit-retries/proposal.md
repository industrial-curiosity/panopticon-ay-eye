# Add GitHub API rate-limit retries

## Why

A child installation can stop partway through a successful public download when
GitHub returns its primary rate-limit response as HTTP `403`. The current
clients retry gateway failures and `429`, but treat every `403` as a permanent
permission failure despite GitHub’s rate-limit headers and recovery guidance.

## What Changes

- Detect GitHub primary and secondary rate limits from response headers and
  retry only those `403` responses after the server-specified recovery delay.
- Apply the same rate-limit behavior to the public launcher, instance bootstrap,
  and child tooling sync paths.
- Keep genuine authorization, repository-not-found, and malformed-response
  failures immediate and clear.
- Display concise retry progress without exposing tokens or response bodies.
- Remove the initialization ordering deadlock so `/panopticon-init` completes
  normal documentation generation and finalization without user intervention.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: GitHub retrieval during launcher, bootstrap, and
  tooling sync must recover from recognized rate limits.

## Impact

Affected code includes `install.py`, `panopticon/bootstrap.py`,
`panopticon/sync.py`, initialization and documentation-generation tooling, and
their unit tests and setup guidance. No external dependencies or credentials are
added.
