# Analysis scope

## Purpose

Define one deterministic policy for excluding illustrative or explicitly ignored material from
Panopticon analysis without suppressing similarly named production paths.

## Requirements

### Requirement: Deterministic illustrative path exclusions

The tooling SHALL exclude a file when any non-filename path component exactly matches, ignoring
case, one of `examples`, `samples`, `fixtures`, `testdata`, `demos`, `scaffolding`, `demo`, or
`scaffold`. It SHALL not use substring matching. Every classification result SHALL include a stable
exclusion reason.

#### Scenario: Illustrative directory is excluded

- **WHEN** a candidate path is `examples/openapi.yaml`
- **THEN** Panopticon excludes it with the reason `illustrative directory: examples`

#### Scenario: Production near-match stays in scope

- **WHEN** a file resides at `src/sample-service/config.yml`
- **THEN** it remains in analysis scope

### Requirement: Explicit analysis-scope hints

The tooling SHALL exclude a complete file when `panopticon-ignore file` appears in one of its first
five nonblank lines. It SHALL exclude a single candidate when
`panopticon-ignore declaration` appears on its declaration line or immediately before it. Hints
SHALL not be persisted in an index.

#### Scenario: Header hint excludes an unconventional illustrative file

- **WHEN** a comment-capable file outside the illustrative path list has `panopticon-ignore file`
  in its header
- **THEN** Panopticon excludes the file and reports the explicit-file-hint reason

#### Scenario: Declaration hint excludes one candidate

- **WHEN** a configuration file marks one topic declaration with
  `panopticon-ignore declaration`
- **THEN** that topic is excluded and subsequent unmarked topics remain in scope

### Requirement: Visible exclusion reporting

Every consumer of analysis scope SHALL report each excluded repository-relative file path or
declaration location and its stable reason. Deterministic parsers, LLM fallback selection, and
doc-drift input preparation SHALL apply scope before parsing or constructing LLM input. Ignored
content SHALL not reach an LLM or persist in an index, component document, or doc-drift finding.
Generated operations documentation SHALL list the currently present illustrative directories that
the path policy excludes.

#### Scenario: A repository has an excluded directory

- **WHEN** documentation is generated for a repository containing `demos/`
- **THEN** `operations.md` visibly lists `demos/` under Panopticon analysis scope

#### Scenario: Excluded content does not reach an LLM

- **WHEN** a changed example workflow matches an interface or dependency pattern
- **THEN** no prompt sent to an LLM contains that workflow and no extraction or drift result names
  it as evidence
