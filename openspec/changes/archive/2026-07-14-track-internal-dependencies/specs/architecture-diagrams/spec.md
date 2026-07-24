# Architecture Diagrams Spec

## MODIFIED Requirements

### Requirement: Org diagram document shape

The org diagram (rendered deterministically from the compiled index by the
master-sync capability) SHALL be a
single document at the instance repo root containing one section per repo that
has at least one external
interface or dependency, ordered alphabetically by repo name. Each section SHALL
contain a relationship
diagram (this repo as the center node, one node per other repo it relates to,
edges labeled by interface or
dependency name and visually distinguished by kind — dashed edges for
interfaces, solid edges for
dependencies) followed by a table listing each external interface or dependency:
kind (interface or
dependency), name, type or ecosystem, direction relative to this repo, the other
repo, and that repo's role
(owner, producer, or consumer).

#### Scenario: Repo with external interfaces gets a section

- **WHEN** the compiled index contains one or more interfaces where a repo
  participates alongside at least
  one other repo
- **THEN** the org diagram document contains that repo's section, alphabetically
  placed, with its
  relationship diagram and interface table

#### Scenario: Repo with only internal interfaces is omitted

- **WHEN** every one of a repo's interface entries is internal-only (see the
  internal-only exclusion rule)
- **THEN** the org diagram document contains no section for that repo

#### Scenario: Repo with external dependencies gets a section

- **WHEN** the compiled dependency index contains one or more dependency entries
  where a repo participates
  alongside at least one other repo (as producer or consumer)
- **THEN** the org diagram document contains that repo's section (or that repo's
  existing interface section
  is extended) with dependency edges rendered visually distinct from interface
  edges, and the repo's table
  includes rows for each external dependency

#### Scenario: Repo with both interfaces and dependencies gets one combined section

- **WHEN** a repo has at least one external interface and at least one external
  dependency
- **THEN** the repo's section contains a single relationship diagram showing
  both kinds of edges and a single
  table listing both, rather than two separate sections

### Requirement: Internal-only interfaces excluded from the org diagram

An interface or dependency entry SHALL be considered internal-only, and excluded
from the org diagram
entirely, when the union of its owner's repo, every producer repo, and every
consumer repo contains exactly
one distinct repo name. An entry SHALL be considered external for a given repo,
and included in that repo's
section, only when this union contains more than one distinct repo name and
includes that repo. This applies
identically to interface entries and dependency entries.

#### Scenario: Single-repo interface excluded

- **WHEN** an interface entry's owner, producers, and consumers all name the
  same single repo
- **THEN** that entry does not appear in any org diagram section

#### Scenario: Cross-repo interface included in both repos' sections

- **WHEN** an interface entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section (direction: produces, other
  repo: B) and in repo B's section
  (direction: consumes, other repo: A)

#### Scenario: Single-repo dependency excluded

- **WHEN** a dependency entry's owner, producer, and consumer all name the same
  single repo (a repo
  depending on its own published package)
- **THEN** that entry does not appear in any org diagram section

#### Scenario: Cross-repo dependency included in both repos' sections

- **WHEN** a dependency entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section (direction: produces, other
  repo: B) and in repo B's section
  (direction: consumes, other repo: A)

## ADDED Requirements

### Requirement: Linked dependency and interface edges deduplicate

The org diagram SHALL render a single edge between two repos, rather than two
separate edges, when a
dependency entry's `links_to_interface` names an interface entry that also
relates the same two repos (same
owner/producer and consumer pairing); the single edge SHALL be labeled to
indicate it represents both the
interface and the dependency.

#### Scenario: Linked generated client collapses to one edge

- **WHEN** a dependency entry has `links_to_interface` naming an interface entry
  that relates the same
  producer and consumer repos
- **THEN** the org diagram's relationship diagram for those repos shows one edge
  between them, not two, and
  the edge's label indicates both the interface and dependency names

#### Scenario: Unlinked dependency and interface between the same repos render separately

- **WHEN** a dependency entry and an interface entry both relate the same two
  repos but no
  `panopticon-dependency-of` hint links them
- **THEN** the org diagram renders both edges separately, without assuming they
  represent the same
  relationship
