# Analysis scope specification

## ADDED Requirements

### Requirement: Deterministic illustrative-path scope

Panopticon SHALL classify a repository path as out of analysis scope when any directory component,
matched case-insensitively as a complete component, is one of `examples`, `samples`, `fixtures`,
`testdata`, `demos`, `scaffolding`, `demo`, or `scaffold`. The classifier SHALL not exclude a
path merely because a longer directory name contains one of those words. Every classifier result
SHALL include a stable exclusion reason.

#### Scenario: Illustrative directory is excluded

- **WHEN** a candidate path is `examples/openapi.yaml`
- **THEN** Panopticon excludes it with the reason `illustrative directory: examples`

#### Scenario: Similar production directory remains in scope

- **WHEN** a candidate path is `src/sample-service/openapi.yaml`
- **THEN** Panopticon keeps it in analysis scope

### Requirement: Explicit ignore annotations

Panopticon SHALL recognize `panopticon-ignore file` only when it appears in one of a text file's
first five nonblank lines, and SHALL exclude that entire file with an explicit-file-hint reason.
It SHALL recognize `panopticon-ignore declaration` only on a declaration line or its immediately
preceding line, and SHALL exclude only the annotated declaration with an explicit-declaration-hint
reason. Hints SHALL be stored in source or configuration files and SHALL not be persisted in an
index.

#### Scenario: Header hint excludes an unconventional illustrative file

- **WHEN** a comment-capable file outside the illustrative path list has
  `panopticon-ignore file` in its header
- **THEN** Panopticon excludes the file and reports the explicit-file-hint reason

#### Scenario: Declaration hint preserves neighboring material

- **WHEN** one declaration in a file has `panopticon-ignore declaration` and another declaration
  does not
- **THEN** Panopticon excludes only the annotated declaration and retains the neighboring
  declaration for analysis

### Requirement: Scope decisions are observable and precede LLM input

Every consumer of analysis scope SHALL report each excluded path or declaration and its reason in
its command or CI summary. Deterministic parsers, LLM fallback selection, and doc-drift input
preparation SHALL apply scope before parsing or constructing LLM input. Ignored content SHALL not
be sent to an LLM or persist in an index, component document, or doc-drift finding.

#### Scenario: Excluded content does not reach an LLM

- **WHEN** a changed example workflow matches an interface or dependency pattern
- **THEN** no prompt sent to an LLM contains that workflow and no extraction or drift result names
  it as evidence
