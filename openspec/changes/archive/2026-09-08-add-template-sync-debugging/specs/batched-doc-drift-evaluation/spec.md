# Batched doc-drift evaluation delta

## ADDED Requirements

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
