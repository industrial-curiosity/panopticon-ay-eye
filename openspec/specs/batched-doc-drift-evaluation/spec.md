# Batched doc-drift evaluation

## Purpose

Define structured planning and isolated batch evaluation for doc-drift checks.

## Requirements

### Requirement: Every relevant doc-drift check SHALL be planned into minimal batches

Doc drift SHALL invoke a structured LLM batch planner before evaluating patch
contents whenever deterministic scope filtering leaves one or more
behavior-bearing product paths. The planner SHALL receive only the retained changed-path list
and available documentation-path list. Its response SHALL assign every retained
changed path exactly once to a minimal coherent batch and SHALL name only
available documentation paths for that batch. An invalid, duplicate, omitted,
or unknown path assignment SHALL be an operational failure.

#### Scenario: Planner isolates independent changes

- **WHEN** a pull request changes two independent product components
- **THEN** the planner returns separate batches with only the documentation
  paths relevant to each component

### Requirement: Batch evaluation SHALL isolate patch and documentation content

Doc drift SHALL evaluate each validated batch independently. An evaluator prompt
SHALL contain only that batch's retained patch content and its assigned
documentation content. A stale reason SHALL cite a changed path from the batch
that produced it. The final doc-drift verdict SHALL combine stale reasons from
all successful batches and retain the existing clean, stale, and operational-
failure exit-code contract.

#### Scenario: One batch finds stale documentation

- **WHEN** one evaluation batch identifies a documentation gap and all other
  batches are clean
- **THEN** doc drift returns the stale verdict with the affected batch's reason
  and existing remediation guidance

### Requirement: Planning and evaluation timeouts SHALL fail immediately with recovery guidance

Doc drift SHALL stop further doc-drift work and return an operational failure if
the planner or any evaluation batch exhausts the configured request attempts.
Its report SHALL identify the failed stage, include safe input byte counts and
path names, and instruct the developer to reduce or split the PR or increase
`PANOPTICON_LLM_TIMEOUT_SECONDS` within its supported range. It SHALL NOT
automatically split and retry the timed-out batch.

#### Scenario: Evaluation batch times out

- **WHEN** an evaluation batch exhausts its configured request attempts
- **THEN** the check fails operationally without evaluating later batches and
  the PR report gives both PR-size and timeout-configuration remedies
