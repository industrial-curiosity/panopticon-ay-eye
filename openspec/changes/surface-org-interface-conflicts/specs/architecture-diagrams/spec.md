# Architecture-diagrams conflict visibility delta

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
