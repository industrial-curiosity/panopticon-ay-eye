## ADDED Requirements

### Requirement: Managed child caller workflow consistency

Bootstrap and local resource sync SHALL use the same fixed managed set of child
caller workflow filenames and the same provider-contract-based caller text.
The managed set SHALL include `panopticon-pr.yml`, `panopticon-merge.yml`,
`panopticon-pr-close.yml`, and `panopticon-resource-sync.yml`. A child that was
bootstrapped before a caller was introduced SHALL be able to acquire that caller
through local resource sync without rerunning bootstrap.

#### Scenario: Bootstrap and sync generate identical caller text

- **GIVEN** the same child configuration and instance provider contract
- **WHEN** bootstrap and local resource sync generate a managed caller
- **THEN** both produce byte-identical workflow content

#### Scenario: Older child acquires a newly managed caller

- **GIVEN** an initialized child was created before a caller filename joined the
  fixed managed set
- **WHEN** local resource sync runs after the instance provides the new caller
  contract
- **THEN** the missing caller is created without rerunning bootstrap
