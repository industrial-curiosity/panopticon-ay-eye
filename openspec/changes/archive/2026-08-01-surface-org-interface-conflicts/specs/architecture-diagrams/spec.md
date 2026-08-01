# Architecture-diagrams conflict visibility delta

## MODIFIED Requirements

### Requirement: Org diagram document shape

The org diagram document SHALL be rendered deterministically from the compiled
index by the master-sync capability. It SHALL be a single document at the
instance repo root containing one section per repo that participates in at least
one interface or in at least one external dependency, ordered alphabetically by
repo name. Each section SHALL contain a relationship diagram and a table listing
every interface in which that repo participates, including an interface used or
managed by that repo alone. Cross-repo interfaces SHALL connect the repo to the
other participating repo through the interface resource; single-repository
interfaces SHALL connect the resource only to that repo. The table SHALL list
kind, name, type or ecosystem, direction relative to the repo, the other repo
when one exists, and that repo's role. Dependencies SHALL retain their existing
external-relationship-only rendering.

#### Scenario: Repo with a single-repository interface gets a section

- **WHEN** the compiled index contains an interface whose owner, producers, and
  consumers all name one repository
- **THEN** the organization document contains that repository's section with
  the interface resource in its diagram and table, without treating it as a
  conflict

#### Scenario: Cross-repo interface appears in every participating section

- **WHEN** an interface has participating repositories A and B
- **THEN** the organization document contains the interface resource in both
  A's and B's sections with the relevant direction and other-repository role

#### Scenario: Repo with only an external dependency gets a section

- **WHEN** the compiled dependency index contains one or more dependencies
  where a repo participates alongside at least one other repo
- **THEN** the organization document contains that repo's section with the
  external dependency rendered using the existing dependency distinction

#### Scenario: Repo with interfaces and dependencies gets one combined section

- **WHEN** a repo participates in one or more interfaces and in one or more
  external dependencies
- **THEN** the repo's section contains one relationship diagram and one table
  listing both kinds of resource

### Requirement: Internal-only interfaces excluded from the org diagram

An interface entry SHALL be included in the organization document for every
repository named by its owner, producers, or consumers, even when that set has
one repository. A dependency entry SHALL remain internal-only, and excluded from
the organization document, when the union of its owner's repo, every producer
repo, and every consumer repo contains exactly one distinct repo name. A
cross-repo dependency SHALL be included for each participating repository.

#### Scenario: Single-repo interface is included

- **WHEN** an interface entry's owner, producers, and consumers all name the
  same single repo
- **THEN** that interface appears in that repo's organization-document section

#### Scenario: Cross-repo interface is included in both repos' sections

- **WHEN** an interface entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section and in repo B's section with
  the appropriate direction and role

#### Scenario: Single-repo dependency is excluded

- **WHEN** a dependency entry's owner, producers, and consumers all name the
  same single repo
- **THEN** that dependency does not appear in any organization-document section

#### Scenario: Cross-repo dependency is included in both repos' sections

- **WHEN** a dependency entry's producer is repo A and consumer is repo B
- **THEN** the dependency appears in repo A's and repo B's sections

## ADDED Requirements

### Requirement: Organization interface-conflict visibility

The generated organization architecture document SHALL render compiled interface
conflicts, including `potential-name-collision` findings, immediately below its
title under the exact heading `## Detected interface conflicts`. Each item SHALL
identify the interface name, its type or involved types, reason, details, and
affected repositories. The heading and section SHALL be omitted when there are
no compiled interface conflicts. Child-repository architecture documents SHALL
NOT be changed by this rendering.

#### Scenario: Organization document has conflicts

- **GIVEN** the compiled interface index contains a confirmed or potential
  interface conflict
- **WHEN** the organization architecture document is rendered
- **THEN** it contains `## Detected interface conflicts` below the title and an
  item describing that conflict

#### Scenario: Organization document has no conflicts

- **GIVEN** the compiled interface index has no interface conflicts
- **WHEN** the organization architecture document is rendered
- **THEN** it omits `## Detected interface conflicts`

### Requirement: Conflicting resources are highlighted in organization diagrams

The organization architecture renderer SHALL distinguish every interface
resource implicated by a compiled interface conflict. In Mermaid, it SHALL
render each affected resource through a dedicated resource node styled with a
red stroke and text and bold label. In the relationship table, it SHALL render
the affected resource name in bold with a red-circle indicator. Clean resources
SHALL retain the existing edge-label and table rendering.

#### Scenario: Confirmed interface conflict highlights its resource

- **GIVEN** a compiled conflict identifies one interface name and type
- **WHEN** an affected repository section is rendered
- **THEN** its Mermaid graph and relationship table visibly highlight that
  interface resource while unrelated resources remain unhighlighted

#### Scenario: Potential collision highlights every involved type

- **GIVEN** a `potential-name-collision` identifies one name with multiple
  involved types
- **WHEN** the organization architecture document is rendered
- **THEN** every relationship row and Mermaid resource for that name and each
  involved type is highlighted in every affected repository section
