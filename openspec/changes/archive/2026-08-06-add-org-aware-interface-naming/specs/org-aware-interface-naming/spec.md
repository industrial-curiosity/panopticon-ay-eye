# Organization-aware Interface Naming Specification

## Purpose

Define local, instance-index-informed canonical naming that prevents generic
cross-repository names while preserving explicit user control through hints.

## ADDED Requirements

### Requirement: Documentation generation uses the instance index before naming

The documentation-generation phase SHALL obtain the configured instance
repository's compiled interface index before it infers or refreshes canonical
interface names. It SHALL use a supplied local instance checkout when available
or otherwise retrieve the compiled index from the configured instance default
branch. A missing compiled index in a fresh instance SHALL be interpreted as an
empty compiled index; an existing index that cannot be retrieved or validated
SHALL stop the naming preflight with actionable recovery guidance.

#### Scenario: Existing organization name is reused

- **WHEN** local evidence identifies a child declaration as the same interface
  as a compatible entry in the retrieved instance index
- **THEN** documentation generation uses that existing canonical name, persists
  it as a local hint when a judgment was needed, regenerates the local index,
  and renders documentation from that regenerated index

#### Scenario: Fresh instance has no compiled index

- **WHEN** documentation generation retrieves no `interfaces/index.json` from a
  newly configured instance repository
- **THEN** it performs the naming preflight against an empty valid compiled
  index and does not report the missing file as an operational failure

#### Scenario: Existing index cannot be used

- **WHEN** a configured instance has a compiled index that cannot be retrieved
  or fails validation
- **THEN** documentation generation stops before minting inferred names and
  reports the instance/index path and recovery action

### Requirement: Inferred names are organization-scale and non-generic

The local naming judgment SHALL infer and persist a non-generic canonical name
as an adjacent `panopticon-interface` hint when local evidence does not identify
an existing compatible interface. Shared durable infrastructure SHALL use
technology plus function, repo-local service surfaces SHALL use durable
repository owner plus surface, and distinct contracts on one backend SHALL have
distinct canonical names. The system SHALL not use a hard-coded generic-name
blacklist or a generic-name warning set in place of this judgment.

#### Scenario: Shared infrastructure receives a technology-function name

- **WHEN** a child declaration is a distinct Kafka event contract for orders
  and no compatible instance entry exists
- **THEN** the local judgment persists a non-generic name such as
  `kafka-order-events`, rather than a bare name such as `events`

#### Scenario: Local surfaces stay distinct across repositories

- **WHEN** two repositories expose unrelated local REST resources that each
  have a raw name of `api`
- **THEN** their local judgments use durable-owner-qualified names and their
  same-type entries do not fuse after shard compilation

#### Scenario: Existing hint is a user override

- **WHEN** a declaration already has an adjacent `panopticon-interface` hint
- **THEN** local naming retains that hint and does not replace it with an
  inferred name

### Requirement: Naming decisions are evidence-led

The local naming judgment SHALL use source or configuration evidence, including
the declaration, protocol, ports, imports, and relevant instance-index entries.
It SHALL not choose a cross-repository identifier solely for lexical symmetry or
aesthetic consistency. When evidence cannot distinguish a possible match from a
distinct interface, it SHALL request user resolution rather than fabricate a
match.

#### Scenario: Ambiguous possible match requires review

- **WHEN** a child interface resembles an instance entry but the available
  source and configuration evidence cannot establish that they are the same
  contract
- **THEN** the local workflow asks for a naming decision and does not write a
  hint that merges the two entries
