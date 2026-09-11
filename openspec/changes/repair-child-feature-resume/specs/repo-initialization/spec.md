# Repository Initialization Delta

## MODIFIED Requirements

### Requirement: Orchestrating init skill

The template repo SHALL include a `panopticon-init` skill (name prefix
`panopticon-`, so the existing skill-download step installs it into the child
repo automatically with no bootstrap script changes) that runs the other Phase
2 skills, enabled feature remediation, and the Phase 3 finalization command in
the correct dependency order from a single invocation, while leaving each
underlying skill independently invocable on its own.

The order SHALL be:

1. `panopticon-interface-naming`.
2. `panopticon-interface-extraction` after step 1, since it depends on the
   naming pass.
3. `panopticon-dependency-naming` after step 2, since a
   `panopticon-dependency-of` hint links a dependency entry to an existing
   interface's canonical name, which requires the interface index built by step
   2 to already exist.
4. `panopticon-dependency-extraction` after step 3, since it depends on the
   dependency naming pass, mirroring how interface extraction depends on
   interface naming.
5. `panopticon-doc-generation` after steps 1–4, since the interface-docs and
   dependency-docs layers are rendered from the local indices that those steps
   build.
6. Each enabled feature's installed skill. Its remediation SHALL use the
   installed child artifacts and SHALL NOT require `features/manifest.json` in
   the child repository.
7. The finalization command (`python3 -m panopticon.init_repo --instance
   <instance>`), which validates enabled feature artifacts through the child
   receipt and installed helper. The instance slug SHALL be self-discovered
   from `.github/workflows/panopticon-pr.yml`.

`panopticon-init` SHALL maintain a checkpoint log at `panopticon/.init-log.json`
recording which of the seven steps have completed. Before starting a step, it
SHALL check the log and skip any step already recorded as complete. It SHALL
update the log immediately after each step completes, so an interrupted run
continues from the first incomplete step rather than restarting from scratch or
skipping ahead into a step whose prerequisites are not met. It SHALL delete the
checkpoint only when finalization succeeds and no agent-remediable feature
finding remains.

Each underlying skill SHALL remain fully usable on its own, independent of
`panopticon-init` and checkpoint-log state, for users who run a single step
directly.

#### Scenario: Fresh run starts at interface naming

- **GIVEN** no checkpoint log exists
- **WHEN** `/panopticon-init` runs
- **THEN** it starts with `panopticon-interface-naming` and records that step
  before continuing

#### Scenario: Dependency naming runs only after the interface index exists

- **GIVEN** interface naming and extraction are recorded as complete
- **WHEN** `panopticon-init` continues
- **THEN** it runs dependency naming next with a populated interface index

#### Scenario: Doc generation runs only after both indices exist

- **GIVEN** interface naming, interface extraction, dependency naming, and
  dependency extraction are recorded as complete
- **WHEN** `panopticon-init` continues
- **THEN** it runs doc generation next with populated interface and dependency
  indices

#### Scenario: Resuming after an interrupted session

- **GIVEN** a checkpoint records completed initialization steps from a prior
  agent session
- **WHEN** `/panopticon-init` runs again
- **THEN** it skips completed steps and resumes at the first incomplete step

#### Scenario: Checkpoint log deleted on successful completion

- **GIVEN** all seven steps have completed, `panopticon/config.json` has been
  written, and no agent-remediable feature finding remains
- **WHEN** `panopticon-init` finishes
- **THEN** `panopticon/.init-log.json` no longer exists in the repo

#### Scenario: Individual skills remain independently invocable

- **WHEN** a user invokes an underlying initialization skill directly
- **THEN** it runs independently of checkpoint-log state

#### Scenario: Finalization instance slug is self-discovered

- **WHEN** `panopticon-init` reaches finalization
- **THEN** it reads the instance slug from the wired caller workflow rather
  than asking the user

#### Scenario: Enabled advisory feature is remediated before finalization

- **GIVEN** the managed feature receipt enables OKF in advisory mode
- **WHEN** `/panopticon-init` reaches feature remediation
- **THEN** it invokes the installed OKF skill, repairs deterministic findings,
  and validates through child-side finalization before completion

#### Scenario: Child feature remediation has no local manifest

- **GIVEN** a child repository has an enabled feature receipt and installed
  helper but no `features/manifest.json`
- **WHEN** `/panopticon-init` revalidates repaired feature artifacts
- **THEN** it continues through finalization without invoking the
  registry-dependent feature-check CLI

#### Scenario: Advisory feature work remains unresolved

- **GIVEN** an enabled advisory feature still has an agent-remediable finding
- **WHEN** its validator completes
- **THEN** `/panopticon-init` retains its checkpoint and reports the installed
  feature skill and viable finalization continuation command instead of
  declaring initialization complete
