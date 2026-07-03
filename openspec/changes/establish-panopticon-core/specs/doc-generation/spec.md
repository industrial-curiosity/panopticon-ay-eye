## ADDED Requirements

### Requirement: Four documentation layers

Doc generation SHALL produce four layers per repo: an architecture overview (purpose, components, data flow,
dependencies), per-component docs following a fixed template, interface docs, and operational docs (how to
run/deploy/test, required configuration). Generated docs SHALL live in the repo's configured documentation
location (adopted or chosen at initialization and recorded in `panopticon/config.json`) so the sync
workflow can copy them to `docs/{repo}/` in the instance repo. Generation and doc updating SHALL be
defined as harness-portable agent skills, so that local runs execute in the user's preferred AI agent harness
with no Panopticon LLM configuration.

#### Scenario: Local doc update through the user's harness

- **WHEN** a user updates a repo's docs locally using the bundled skills in their own agent harness
- **THEN** the four-layer structure and templates are honored without `PANOPTICON_LLM_*` configuration

#### Scenario: Initial generation

- **WHEN** doc generation runs on a repo during initialization
- **THEN** all four layers exist in the repo's docs location, each following its template

### Requirement: Interface docs rendered from the index

Interface docs SHALL be a human-readable rendering of the repo's local interface index (deterministic
rendering, not LLM prose), so that interface docs can never disagree with the index.

#### Scenario: Index and interface docs stay consistent

- **WHEN** the local index changes and docs are regenerated
- **THEN** the interface docs reflect exactly the entries in the updated index

### Requirement: Doc-vs-code drift detection

The tooling SHALL provide an LLM-based drift check that, given a PR's code/configuration changes and the
current docs, judges whether documentation updates are required — developers keep their repo's docs and index
up to date locally with their own agents, and CI verifies that they have. When docs are stale the check SHALL
fail loudly and clearly — naming which docs are stale, why, and what the developer must do. Org gating
configuration MAY downgrade the check to advisory.

#### Scenario: Code change affecting documented behavior

- **WHEN** a PR changes a component's public behavior without touching its docs
- **THEN** the drift check fails, reporting in the PR comment which docs are stale, why, and what the
  developer must update

#### Scenario: Docs updated alongside code

- **WHEN** a PR updates docs consistently with its code changes
- **THEN** the drift check passes and says so in the CI summary

### Requirement: Regeneration updates in place

Doc regeneration SHALL update the existing generated docs in place, preserving the layer structure, and MUST
NOT create parallel copies or leave stale sections for removed components.

#### Scenario: Component removed from codebase

- **WHEN** docs are regenerated after a component is deleted
- **THEN** that component's per-component doc is removed and references to it are gone from the overview
