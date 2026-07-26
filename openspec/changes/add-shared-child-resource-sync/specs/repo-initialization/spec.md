# Repo initialization shared sync delta

## ADDED Requirements

### Requirement: Bootstrap wires the child resource-sync caller

The bootstrap installer SHALL write a stable child
`.github/workflows/panopticon-resource-sync.yml` caller for the shared child
resource synchronization workflow. The caller SHALL expose only manual dispatch,
use the child default branch's workflow context, map the instance-read secret
explicitly, and grant only the permissions needed to push an automation branch
and create or update a child pull request.

#### Scenario: New child bootstrap installs the caller

- **WHEN** bootstrap initializes a child repository
- **THEN** it writes the stable resource-sync caller alongside the existing
  Panopticon workflow callers

#### Scenario: Bootstrap refresh preserves the caller contract

- **GIVEN** an already initialized child repository
- **WHEN** bootstrap refreshes its managed workflow files
- **THEN** it updates the resource-sync caller in place without duplicating it
  or rerunning initialization
