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

### Requirement: Batched doc-drift evaluation SHALL expose safe debug progress

The doc-drift command SHALL provide an opt-in debug mode that logs the
retained behavior-bearing paths, batch-planning start and validated result,
each batch's changed paths and selected documentation paths, and each batch
evaluation's start and completion. When a request diagnostic is available, the
debug output SHALL use only its existing safe fields. The debug output SHALL
NOT include patch content, documentation content, prompts, model responses,
endpoint URLs, credentials, secret names or values, or resolved configuration
values. Built-in provider PR workflows SHALL enable this mode for the
doc-drift step; the Actions summary and PR report SHALL remain outcome-focused
and exclude this debug trace.

#### Scenario: Planner produces two batches

- **WHEN** doc drift runs in debug mode and its planner assigns two batches
- **THEN** the step log identifies the retained paths and each batch's changed
  paths and documentation paths before their evaluations start

#### Scenario: Evaluation request completes

- **WHEN** a doc-drift batch evaluation completes in debug mode
- **THEN** the step log records that batch's completion and any available safe
  request diagnostic without logging request or response content

#### Scenario: Normal report remains concise

- **WHEN** a built-in provider workflow runs doc drift with debug mode enabled
- **THEN** its Actions summary and PR report contain the final outcome and
  remediation rather than the debug trace
