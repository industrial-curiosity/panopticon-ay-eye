# Interface-indexing conflict visibility delta

## ADDED Requirements

### Requirement: Potential same-name interface collisions

The compiled interface index SHALL contain one deterministic
`potential-name-collision` conflict when interface objects sharing a canonical
name use different types and their participating repository sets are disjoint.
The conflict SHALL identify the canonical name, every involved type and
repository, and that it is a potential rather than confirmed semantic conflict.
The compiler SHALL recompute this conflict on every rebuild without an LLM call.
Local indexes and instance shards SHALL NOT contain this conflict.

#### Scenario: Disjoint repository sets use different types under one name

- **GIVEN** one repository uses `order-processing-queue` as `rest` and another
  repository uses it as `sqs`, with no participating repository in common
- **WHEN** the compiled index is rebuilt
- **THEN** it contains one `potential-name-collision` conflict for
  `order-processing-queue` that identifies both types and repositories

#### Scenario: A type migration overlaps a participating repository

- **GIVEN** same-name interface objects of different types share at least one
  participating repository
- **WHEN** the compiled index is rebuilt
- **THEN** it does not create a `potential-name-collision` conflict solely from
  that type difference

#### Scenario: A shard change removes the potential collision

- **GIVEN** a compiled index contains a `potential-name-collision`
- **WHEN** a shard update removes the disjoint type mismatch and the index is
  rebuilt
- **THEN** the derived conflict is absent from the rebuilt compiled index
