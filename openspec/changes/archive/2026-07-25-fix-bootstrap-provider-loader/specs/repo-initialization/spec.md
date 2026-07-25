# Bootstrap provider loader delta

## ADDED Requirements

### Requirement: Default bootstrap payload loads its import dependencies

The default payload loader SHALL, when the fetched instance installer delegates
to the template's bootstrap payload, fetch and register every direct
`panopticon` module dependency required to import that bootstrap module before
executing it. The modules SHALL be loaded through the existing validated,
authenticated GitHub-contents path into the in-memory `panopticon` package;
the loader SHALL not require installation to disk or a `PYTHONPATH` change.

#### Scenario: Default bootstrap imports the provider registry

- **GIVEN** an uncustomized instance installer delegates to a bootstrap payload
  that imports `panopticon.providers`
- **WHEN** the public launcher loads and executes that payload
- **THEN** it fetches and registers `panopticon.providers` before evaluating
  `panopticon.bootstrap`, and the bootstrap begins without a module-not-found
  error

#### Scenario: Provider registry retrieval is invalid

- **GIVEN** the default bootstrap requires `panopticon.providers`
- **WHEN** the GitHub contents API returns an invalid provider-module payload
- **THEN** the launcher fails with its controlled invalid-payload error before
  executing the bootstrap module
