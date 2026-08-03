# Documentation generation specification delta

## MODIFIED Requirements

### Requirement: Four documentation layers

Doc generation SHALL produce four layers per repo: an architecture overview (purpose, components,
data flow, dependencies, and an architecture diagram section per the architecture-diagrams
capability), per-component docs following a fixed template, interface docs, and operational docs
(how to run/deploy/test, required configuration, and a managed `## Panopticon analysis scope`
section). Generated docs SHALL live in the repo's configured documentation location (adopted or
chosen at initialization and recorded in `panopticon/config.json`) so the sync workflow can copy
them to `docs/{repo}/` in the instance repo. Generation and doc updating SHALL be defined as
harness-portable agent skills, so that local runs execute in the user's preferred AI agent harness
with no Panopticon LLM configuration. The managed analysis-scope section SHALL list each actual
repository directory excluded by the illustrative-path policy, its reason, the complete default
directory set, and the explicit file and declaration hint forms.

#### Scenario: Local doc update through the user's harness

- **WHEN** a user updates a repo's docs locally using the bundled skills in their own agent harness
- **THEN** the four-layer structure and templates are honored without `PANOPTICON_LLM_*` configuration

#### Scenario: Initial generation

- **WHEN** doc generation runs on a repo during initialization
- **THEN** all four layers exist in the repo's docs location, each follows its template, the architecture overview includes the `## Architecture diagram` section, and `operations.md` includes `## Panopticon analysis scope`

#### Scenario: Repository has illustrative directories

- **WHEN** a repository contains `examples/` and `fixtures/`
- **THEN** its managed analysis-scope section lists both repository-relative directories and their illustrative-path exclusion reasons

## ADDED Requirements

### Requirement: Scope-aware documentation generation and drift input

Component discovery and documentation input preparation SHALL use the shared analysis-scope policy. The doc-drift check SHALL remove excluded paths and ignored declaration text before constructing its behavior-bearing evidence set or LLM prompt. If no behavior-bearing material remains after scope filtering, it SHALL return a clean verdict without invoking an LLM.

#### Scenario: Ignored change produces no drift finding

- **WHEN** a pull request changes only an interface-shaped file under `demos/`
- **THEN** doc drift returns a clean verdict without invoking an LLM or naming that file as stale evidence
