## MODIFIED Requirements

### Requirement: Orchestrating init skill

The template repo SHALL include a `panopticon-init` skill (name prefix `panopticon-`, so the existing
skill-download step installs it into the child repo automatically with no bootstrap script changes) that
runs the other Phase 2 skills and the Phase 3 finalization command in the correct dependency order, from
a single invocation, while leaving each underlying skill independently invocable on its own.

The order SHALL be:

1. `panopticon-interface-naming`
2. `panopticon-interface-extraction` — after step 1, since it depends on the naming pass
3. `panopticon-dependency-naming` — after step 2, since a `panopticon-dependency-of` hint links a
   dependency entry to an existing interface's canonical name, which requires the interface index
   built by step 2 to already exist
4. `panopticon-dependency-extraction` — after step 3, since it depends on the dependency naming
   pass, mirroring how interface-extraction depends on interface-naming
5. `panopticon-doc-generation` — after steps 1–4, since the interface-docs and dependency-docs
   layers are rendered from the local indices (`panopticon/index.json` and the dependency shard)
   that those steps build; running doc-generation first has no index to render from
6. The finalization command (`python3 -m panopticon.init_repo --instance <instance>`) — the instance
   slug SHALL be self-discovered by reading the `uses:` line already wired into
   `.github/workflows/panopticon-pr.yml`, rather than requiring the user to supply it

`panopticon-init` SHALL maintain a checkpoint log at `panopticon/.init-log.json` recording which of the
six steps have completed. Before starting a step, it SHALL check the log and skip any step already
recorded as complete. It SHALL update the log immediately after each step completes, so an interrupted
run — including one resumed in a new agent session with no memory of the prior one — continues from the
first incomplete step rather than restarting from scratch or skipping ahead into a step whose
prerequisites aren't met. Once all six steps have completed and `panopticon/config.json` has been
written, `panopticon-init` SHALL delete the checkpoint log — a completed initialization has no further
use for it, and it SHALL NOT remain in the repo afterward.

Each of the six skills SHALL remain fully usable on its own, independent of `panopticon-init` and of any
checkpoint log state, for users who want to run a single step directly.

#### Scenario: Fresh run starts at interface naming

- **GIVEN** no checkpoint log exists
- **WHEN** `/panopticon-init` runs
- **THEN** it starts with `panopticon-interface-naming`, then creates the checkpoint log recording that
  step's completion before continuing

#### Scenario: Dependency naming runs only after the interface index exists

- **GIVEN** the checkpoint log shows `panopticon-interface-naming` and `panopticon-interface-extraction`
  complete
- **WHEN** `panopticon-init` continues
- **THEN** it runs `panopticon-dependency-naming` next, with a populated interface index available for
  `panopticon-dependency-of` hints to reference

#### Scenario: Doc generation runs only after both indices exist

- **GIVEN** the checkpoint log shows `panopticon-interface-naming`, `panopticon-interface-extraction`,
  `panopticon-dependency-naming`, and `panopticon-dependency-extraction` all complete
- **WHEN** `panopticon-init` continues
- **THEN** it runs `panopticon-doc-generation` next, with a populated interface index and dependency
  shard to render `interfaces.md` and the dependency-docs layer from

#### Scenario: Resuming after an interrupted session

- **GIVEN** a checkpoint log recording `panopticon-interface-naming`, `panopticon-interface-extraction`,
  and `panopticon-dependency-naming` as complete, from a prior agent session that did not finish
- **WHEN** `/panopticon-init` is invoked again, in a new agent session with no memory of the prior one
- **THEN** it skips the three completed steps and resumes at `panopticon-dependency-extraction`

#### Scenario: Checkpoint log deleted on successful completion

- **GIVEN** all six steps have completed and `panopticon/config.json` has been written
- **WHEN** `panopticon-init` finishes
- **THEN** `panopticon/.init-log.json` no longer exists in the repo

#### Scenario: Individual skills remain independently invocable

- **WHEN** a user invokes `/panopticon-doc-generation` or `/panopticon-dependency-naming` directly
  instead of `/panopticon-init`
- **THEN** it runs as its own standalone skill, unaffected by whether a checkpoint log exists

#### Scenario: Finalization instance slug is self-discovered

- **WHEN** `panopticon-init` reaches the finalization step
- **THEN** it determines the instance slug by reading the `uses:` line in
  `.github/workflows/panopticon-pr.yml` rather than asking the user for it

### Requirement: Agent-driven initialization

Repo initialization SHALL follow a three-phase sequence:

**Phase 1 — Bootstrap (deterministic, no AI):** the bootstrap installer script installs skills, vendors
the local-tooling subset of the `panopticon` Python package, and wires caller workflows in the child
repo, then outputs the `/panopticon-init` prompt. No `PANOPTICON_LLM_*` or local instance clone is
required.

**Phase 2 — Agent (AI-driven):** the user's preferred AI agent follows the `panopticon-init` skill
invoked by the bootstrap script's printed prompt, which sequences the interface-naming,
interface-extraction, dependency-naming, dependency-extraction, and doc-generation skills in dependency
order (with a resumable checkpoint log) to build the local interface index
(`panopticon/index.json`), the local dependency shard, and generate the four-layer documentation. No
`PANOPTICON_LLM_*` configuration is required locally; the agent uses its own harness.

**Phase 3 — Finalization (deterministic):** the finalization step validates that the agent-produced docs
and index meet requirements (all four layers present and following their templates; schema-valid index)
and writes `panopticon/config.json` — the initialization flag — only after that validation passes.
`panopticon/config.json` SHALL be the last artifact created during initialization.

#### Scenario: Successful initialization

- **GIVEN** the bootstrap script has installed skills and workflows and printed the `/panopticon-init`
  prompt
- **WHEN** the agent has generated docs and indices and the finalization step runs
- **THEN** `panopticon/config.json` is written as the final artifact, and the repo is fully initialized

#### Scenario: Agent output incomplete at finalization

- **WHEN** the finalization step runs before the agent has produced all four documentation layers
- **THEN** no config file is written and the tooling reports exactly which requirements are unmet
