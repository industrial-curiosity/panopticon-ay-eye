# Tooling Currency Specification Delta

## ADDED Requirements

### Requirement: Tooling-currency reads the authoritative instance manifest

The advisory tooling-currency check SHALL parse the versioned data-only
`panopticon/local-tooling.json` manifest from the already checked-out instance
repository. It SHALL validate the same schema and module-path constraints as
bootstrap and local sync, and SHALL compare only the manifest-listed child
tooling modules. It SHALL NOT execute manifest content or use a child manifest
copy.

#### Scenario: Instance manifest selects compared tooling

- **GIVEN** a child has a stale or absent manifest copy
- **WHEN** the PR workflow runs tooling-currency against an instance checkout
- **THEN** it determines managed tooling from the validated instance manifest
  and reports content drift only for those modules

#### Scenario: Invalid instance manifest remains advisory

- **GIVEN** the instance checkout contains an invalid local-tooling manifest
- **WHEN** tooling-currency runs
- **THEN** it emits a non-blocking warning naming the manifest error and does
  not write or delete child files
