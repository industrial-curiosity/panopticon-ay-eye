# Master sync delta

## ADDED Requirements

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
