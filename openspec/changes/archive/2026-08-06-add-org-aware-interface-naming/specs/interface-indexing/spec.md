# Interface Indexing Specification Delta

## ADDED Requirements

### Requirement: Organization-aware judgments preserve deterministic indexes

Local organization-aware naming judgments SHALL be persisted as source or
configuration hints before extraction writes a shard. Extraction, PR
simulation, shard merge, and compiled-index rebuild SHALL resolve those hints
deterministically and SHALL not require access to the instance index or an LLM
to reproduce the stored result.

#### Scenario: Repeated extraction after a local naming judgment

- **WHEN** local documentation generation has persisted a canonical-name hint
  after consulting the instance index
- **THEN** a later local or CI extraction produces the same canonical key using
  the hint without an LLM call or a second instance-index comparison
