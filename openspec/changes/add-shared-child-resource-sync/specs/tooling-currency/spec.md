# Tooling currency shared sync delta

## ADDED Requirements

### Requirement: Shared child resource synchronization workflow

The template SHALL provide a reusable workflow that refreshes an initialized
child repository's managed Panopticon skills and vendored local tooling from its
configured instance repository. A child SHALL invoke it through a stable local
manual caller. When the refresh changes managed resources, the workflow SHALL
create or update one automation-owned pull request against the child default
branch. When no resources differ, it SHALL succeed without creating a branch or
pull request.

#### Scenario: Manual resource sync creates a reviewable pull request

- **GIVEN** an initialized child repository whose managed Panopticon resources
  differ from its instance repository
- **WHEN** a maintainer runs the child resource-sync workflow from the child
  default branch
- **THEN** the workflow creates or updates one pull request containing only the
  refreshed managed resources

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
