# Analysis scope

## Purpose

Define one deterministic policy for excluding illustrative or explicitly ignored material from
Panopticon analysis without suppressing similarly named production paths.

### Requirement: Deterministic illustrative path exclusions

The tooling SHALL exclude a file when any non-filename path component exactly matches, ignoring
case, one of `examples`, `samples`, `fixtures`, `testdata`, `demos`, `scaffolding`, `demo`, or
`scaffold`. It SHALL not use substring matching.

#### Scenario: Production near-match stays in scope

- **WHEN** a file resides at `src/sample-service/config.yml`
- **THEN** it remains in analysis scope

### Requirement: Explicit analysis-scope hints

The tooling SHALL exclude a complete file when `panopticon-ignore file` appears in one of its first
five nonblank lines. It SHALL exclude a single candidate when
`panopticon-ignore declaration` appears on its declaration line or immediately before it.

#### Scenario: Declaration hint excludes one candidate

- **WHEN** a configuration file marks one topic declaration with
  `panopticon-ignore declaration`
- **THEN** that topic is excluded and subsequent unmarked topics remain in scope

### Requirement: Visible exclusion reporting

Extraction summaries SHALL identify each excluded repository-relative file path or declaration
location and a stable reason without revealing unrelated file contents. Generated operations
documentation SHALL list the currently present illustrative directories that the path policy
excludes.

#### Scenario: A repository has an excluded directory

- **WHEN** documentation is generated for a repository containing `demos/`
- **THEN** `operations.md` visibly lists `demos/` under Panopticon analysis scope
