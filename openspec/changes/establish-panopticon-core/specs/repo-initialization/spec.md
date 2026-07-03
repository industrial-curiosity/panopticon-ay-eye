## ADDED Requirements

### Requirement: Agent-driven initialization

Repo initialization SHALL be performed by the user's preferred AI agent following the bundled skills:
generating the four-layer documentation and building the local interface index, with no `PANOPTICON_LLM_*`
configuration required locally. The deterministic tooling, run from an instance fork against the child repo,
SHALL wire the repo with thin caller workflows referencing the instance repo's reusable workflows at the
org-configured ref, SHALL validate that the agent-produced docs and index meet the project requirements (all
four layers present and following their templates; schema-valid index), and SHALL write the repo's Panopticon
config file (`panopticon/config.json`) — which serves as the initialization flag and records repo-level
settings such as the documentation location — only after that validation passes.

#### Scenario: Successful initialization

- **WHEN** the user's agent has generated docs and index and the deterministic validation passes
- **THEN** the repo contains caller workflows pointing at the instance repo's reusable workflows, generated
  docs, a local `panopticon/index.json`, and `panopticon/config.json`

#### Scenario: Docs do not yet meet requirements

- **WHEN** validation runs before the agent has produced all four documentation layers
- **THEN** no config file is written and the tooling reports exactly which requirements are unmet

### Requirement: Org-level secret prerequisites

The init tooling SHALL verify that `PANOPTICON_LLM_API_KEY`, `PANOPTICON_LLM_ENDPOINT`, and
`PANOPTICON_INSTANCE_TOKEN` are configured as org-level secrets available to the child repo — they are
consumed only by the shared CI workflows — and SHALL report clear setup instructions for any that are missing
rather than failing opaquely. Child repos MUST NOT require per-repo secret or environment configuration: the
caller workflows a child repo receives are trivial references to the shared workflows. Missing secrets SHALL
NOT block the local initialization steps themselves.

#### Scenario: Missing instance token

- **WHEN** initialization runs for a repo whose org has not configured `PANOPTICON_INSTANCE_TOKEN`
- **THEN** it reports which org-level secret is missing and how to configure it before workflow wiring is
  considered complete

### Requirement: Documentation location adoption

When the child repo already has documentation, initialization SHALL adopt that location as the documentation
source and align its content to Panopticon's four layers as much as possible — it does not need to be perfect.
When no documentation exists, the user SHALL be prompted for the desired location, with `docs/` as the
default. The chosen location SHALL be recorded in `panopticon/config.json` so CI and sync workflows can
locate the docs.

#### Scenario: Repo with existing docs

- **WHEN** initialization runs on a repo with an existing documentation folder
- **THEN** that folder is configured as the doc source and its content is aligned to the four layers where
  feasible

#### Scenario: Repo without docs

- **WHEN** initialization runs on a repo with no existing documentation
- **THEN** the user is prompted for the desired location, defaulting to `docs/`

### Requirement: Idempotent re-initialization

Re-initializing an already-initialized repo SHALL detect `panopticon/config.json` and update workflow wiring,
docs, and index in place without duplicating workflows or docs.

#### Scenario: Re-run on initialized repo

- **WHEN** initialization runs on a repo that already has `panopticon/config.json`
- **THEN** existing Panopticon workflows and docs are updated in place and no duplicate files are created
