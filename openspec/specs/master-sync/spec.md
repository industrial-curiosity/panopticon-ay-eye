### Requirement: Docs and index push on merge to main

When a child repo merges to its default branch, the sync workflow SHALL push directly to the instance repo's
default branch: copy the repo's generated docs to `docs/{repo}/`, replace the repo's index shard wholesale,
and rebuild the compiled index. No PR is opened in the instance repo.

#### Scenario: Merge to main syncs the instance repo

- **WHEN** a PR merges to main in an initialized child repo
- **THEN** the instance repo's default branch contains the repo's updated docs under `docs/{repo}/`, the
  replaced shard, and a compiled index rebuilt from all shards

### Requirement: Conflict issues in both repos

When the merge produces conflict entries, the sync workflow SHALL open an issue in the instance repo and an
issue in the child repo, each describing the conflicting entries and linking to the other issue. At most one
open Panopticon conflict issue SHALL exist per child repo in each repository: subsequent merges SHALL update
the existing issue rather than opening duplicates.

#### Scenario: Merge produces a conflict

- **WHEN** the shard merge creates one or more conflict entries
- **THEN** issues are opened in both the instance repo and the child repo describing the conflicts and
  cross-linking each other

#### Scenario: Conflict persists across merges

- **WHEN** a later merge produces conflicts while the repo's conflict issue is still open
- **THEN** the existing issues are updated in place and no duplicate issues are opened

### Requirement: Concurrent-merge safety

The sync workflow SHALL handle concurrent pushes from multiple child repos with a fetch-rebase-retry loop.
Because shards are per-repo files, retries MUST re-run only the compiled-index rebuild, never modify another
repo's shard.

#### Scenario: Two repos merge simultaneously

- **WHEN** two child repos push to the instance repo at nearly the same time and one push is rejected
- **THEN** the rejected workflow fetches, rebuilds the compiled index over the new state, and retries until
  its shard update lands, leaving both repos' shards intact

### Requirement: Instance branch lifecycle

When a PR closes (merged or abandoned), the matching `{repo}/{branch}` branch in the instance repo SHALL be
deleted. Pruning of orphaned branches beyond the close trigger is deliberately deferred until explicitly
required.

#### Scenario: PR merged

- **WHEN** a PR for branch `feature/x` of repo `svc-a` is merged or closed
- **THEN** the instance repo branch `svc-a/feature/x` is deleted
