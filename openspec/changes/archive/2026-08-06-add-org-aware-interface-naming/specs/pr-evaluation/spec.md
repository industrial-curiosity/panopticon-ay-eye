# PR Evaluation Specification Delta

## ADDED Requirements

### Requirement: PR evaluation explains instance-index candidate matches

The PR workflow SHALL prepare a bounded, relevant set of instance interface
candidates for each changed or proposed child interface after downloading the
instance compiled index and before publishing its combined report. The CI LLM
SHALL classify each candidate as likely same interface, likely distinct
interface, or insufficient evidence, and cite available child and instance
evidence. This analysis SHALL be advisory and SHALL not mutate hints, the local
index, the deterministic simulation result, or gate state.

#### Scenario: Semantic near-match is surfaced without automatic merge

- **WHEN** the proposed child index has an interface that resembles an instance
  entry but deterministic simulation finds no exact conflict
- **THEN** the PR report prominently identifies the candidate and its evidence
  as advisory follow-up without changing either index

### Requirement: PR report visualizes prospective child architecture

The maintained Panopticon PR report comment SHALL include the validated Mermaid
block from the child architecture overview, the deterministic prospective-merge
result, and the instance-index candidate analysis. The workflow SHALL update
its marker-owned comment instead of overwriting the PR author's description.

#### Scenario: Report includes a valid architecture diagram

- **WHEN** a child PR has a valid Mermaid architecture diagram
- **THEN** the maintained Panopticon report comment renders that Mermaid block
  beneath a prospective-architecture heading with the merge findings

#### Scenario: Diagram is unavailable

- **WHEN** the child diagram is missing or malformed
- **THEN** the report explicitly identifies the unavailable diagram and retains
  the existing diagram-check outcome without fabricating a replacement diagram

### Requirement: Child conflict-gating override takes precedence

The PR workflow SHALL determine the effective `interface-conflict` gating mode
by reading a valid child-repository `panopticon/config.json` override first,
then the instance repository's `panopticon.config.json` value, then the built-in
`advisory` default. Both advisory and blocking outcomes SHALL publish the same
prominent conflict warning and effective-policy explanation. Only the blocking
outcome SHALL fail the conflict check.

#### Scenario: Child retains advisory mode against a blocking instance default

- **WHEN** the instance config marks `interface-conflict` as `blocking` and the
  child config explicitly marks it `advisory`
- **THEN** the PR reports the conflict and the child override prominently, but
  the conflict check succeeds

#### Scenario: Child escalates an advisory instance default

- **WHEN** the instance config is advisory and the child config marks
  `interface-conflict` as `blocking`
- **THEN** a detected deterministic conflict produces the prominent warning and
  fails the conflict check
