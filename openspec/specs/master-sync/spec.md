# Master sync

## Purpose

Define how child repositories synchronize generated documentation and index data to the Panopticon instance,
report conflicts, handle concurrent updates, clean up instance branches, and rebuild organization diagrams.

## Requirements

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

### Requirement: Org diagram rebuild on merge to main

When a child repo merges to its default branch, the sync workflow SHALL deterministically rebuild the org
diagram document (architecture-diagrams capability) from the freshly compiled index, immediately after
`compile_index()` produces the new compiled state, and include the result in the same commit as the compiled
index rebuild. This rebuild SHALL require no LLM call and no dependency on any child repo having a diagram
section yet — it is derived entirely from the compiled index's `owner`/`producer`/`consumer` data.

#### Scenario: Merge to main rebuilds the org diagram

- **WHEN** a PR merges to main in an initialized child repo and the merge sync workflow runs
- **THEN** the instance repo's default branch contains an org diagram document reflecting the freshly
  compiled index, committed alongside the compiled index itself

#### Scenario: Org diagram rebuild does not depend on per-repo diagrams existing

- **WHEN** a child repo has no `## Architecture diagram` section in its own `architecture.md`
- **THEN** the org diagram rebuild still succeeds, using only that repo's compiled-index entries; the repo's
  section (if it has external interfaces) links to `docs/{repo}/architecture.md` regardless of whether that
  file itself contains a diagram section

### Requirement: Shared sync and cleanup failures have actionable summaries

The shared merge-sync and PR-close workflows SHALL write the detected failure reason and a corrective action
to the GitHub Actions step summary before any explicit non-zero exit caused by initialization failure,
instance-token unavailability, shard-merge failure, exhausted instance-branch push retries, conflict-issue
preparation failure, or instance-branch deletion failure. Their concise workflow annotations SHALL direct
the maintainer to the summary.

#### Scenario: Merge sync cannot publish after retries

- **WHEN** the merge-sync workflow exhausts its configured instance-branch push retries
- **THEN** it exits non-zero and its step summary states that concurrent updates exhausted the retry budget
  and instructs the maintainer to rerun against the latest instance state

#### Scenario: PR-close branch deletion fails

- **WHEN** the PR-close workflow cannot delete the matching derived instance branch for a reason other than
  an already-absent branch
- **THEN** it exits non-zero and its step summary identifies the branch, the deletion failure, and the
  instruction to verify the instance token's repository-contents permission before rerunning
