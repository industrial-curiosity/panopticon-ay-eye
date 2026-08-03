# Interface indexing specification delta

## MODIFIED Requirements

### Requirement: Deterministic parser framework

The tooling SHALL provide a parser registry where each parser is a self-contained Python module
exposing `detect(repo_root)` and `extract(repo_root)`, registered by interface type. Extraction
SHALL run every parser whose `detect` returns true. Before parser detection or extraction, shared
file iteration SHALL apply the analysis-scope policy. Parsers MUST NOT import org-specific code or
require dependencies beyond the core tooling's requirements. A parser that supports
declaration-level annotations SHALL preserve the candidate declaration line so the shared
analysis-scope filter can exclude that declaration.

#### Scenario: Parser handles its interface type

- **WHEN** extraction runs on a repo containing an OpenAPI specification
- **THEN** the REST parser detects it and emits index entries derived from the specification

#### Scenario: Parser skips an illustrative specification

- **WHEN** an OpenAPI specification is under `examples/`
- **THEN** interface extraction does not emit an entry from that file and reports its illustrative-directory exclusion

### Requirement: LLM extraction fallback with parser-gap reporting

Extraction SHALL fall back to the LLM for candidate interfaces not covered by any deterministic
parser through the user's agent locally and the agent runtime in CI. In CI, LLM evaluation SHALL
be scoped to changed files plus the minimal context required to understand them; full-repo
extraction happens locally through the user's agent. Analysis scope SHALL filter candidate files
and annotated declarations before the LLM prompt is assembled. LLM-extracted entries SHALL be
tagged `"extracted_by": "llm"`, and the workflow summary SHALL include a warning recommending
creation of a deterministic parser for each interface type extracted this way.

#### Scenario: Unparsed interface type found

- **WHEN** extraction finds a message-queue interface for which no parser is registered
- **THEN** the LLM extractor emits the entry tagged `"extracted_by": "llm"` and the workflow summary recommends generating a parser for that interface type

#### Scenario: Ignored fallback declaration is omitted

- **WHEN** an otherwise eligible fallback file contains an annotated ignored declaration
- **THEN** the LLM prompt omits the annotation and declaration, and no extracted interface names that declaration
