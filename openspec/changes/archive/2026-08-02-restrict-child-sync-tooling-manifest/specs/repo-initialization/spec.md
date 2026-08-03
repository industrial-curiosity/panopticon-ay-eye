# Repo Initialization Delta

## ADDED Requirements

### Requirement: Child sync uses the explicit local-tooling manifest

Child bootstrap and child resource sync SHALL manage the same explicit,
instance-owned local-tooling manifest. Resource sync SHALL download the
manifest from the selected instance ref on every run and SHALL NOT use a child
copy to select modules. It SHALL fetch, preview, and overwrite only
manifest-listed modules, SHALL NOT add CI-only runtime modules, and SHALL NOT
delete existing child files outside the manifest.

#### Scenario: Sync encounters CI-only module

- **WHEN** the instance tree contains a CI-only `panopticon/` module outside
  the local-tooling manifest
- **THEN** child sync neither reports nor writes that module

#### Scenario: Sync refreshes child-safe tooling

- **WHEN** a manifest-listed module changes in the instance
- **THEN** preview reports it and apply refreshes it in the child repository

#### Scenario: Child has a stale manifest copy

- **WHEN** a child repository contains an older local-tooling manifest
- **THEN** resource sync uses the manifest downloaded from the selected
  instance ref to select its modules

#### Scenario: Child has an unmanaged module

- **WHEN** a child repository contains a `panopticon/` file outside the
  local-tooling manifest
- **THEN** child sync leaves that file unchanged
