# Tooling currency specification delta

## MODIFIED Requirements

### Requirement: Shared child resource synchronization workflow

The template SHALL provide a reusable workflow that refreshes an initialized
child repository's managed Panopticon skills and vendored local tooling from its
configured instance repository. A child SHALL invoke it through a stable local
manual caller. When the refresh changes managed resources, the workflow SHALL
use its automation branch and update only an open automation-owned pull request
against the child default branch. When no such open pull request exists,
including when a prior automation pull request was merged or closed, the
workflow SHALL create a new automation-owned pull request against the child
default branch. When no resources differ, it SHALL succeed without creating a
branch or pull request.

#### Scenario: Manual resource sync updates an open reviewable pull request

- **GIVEN** an initialized child repository whose managed Panopticon resources
  differ from its instance repository
- **AND** an open automation-owned pull request exists for the resource-sync
  branch against the child default branch
- **WHEN** a maintainer runs the child resource-sync workflow from the child
  default branch
- **THEN** the workflow updates that open pull request with only the refreshed
  managed resources

#### Scenario: Manual resource sync creates a pull request after a prior one closes

- **GIVEN** an initialized child repository whose managed Panopticon resources
  differ from its instance repository
- **AND** the prior automation-owned pull request for the resource-sync branch
  was merged or closed
- **WHEN** a maintainer runs the child resource-sync workflow from the child
  default branch
- **THEN** the workflow creates a new pull request containing only the
  refreshed managed resources
- **AND** the workflow does not update the merged or closed pull request

#### Scenario: Current resources create no pull request

- **GIVEN** an initialized child repository whose managed Panopticon resources
  match its instance repository
- **WHEN** a maintainer runs the child resource-sync workflow from the child
  default branch
- **THEN** the workflow succeeds without creating a branch or pull request

#### Scenario: Non-default branch cannot use the instance credential

- **GIVEN** a resource-sync workflow dispatch targets a child branch other than
  the repository default branch
- **WHEN** the shared workflow begins
- **THEN** it fails before mapping or using the instance-read credential and
  does not create a pull request
