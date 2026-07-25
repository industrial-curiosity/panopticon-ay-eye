# Repo initialization delta: vendored provider tooling and reports

## MODIFIED Requirements

### Requirement: Local tooling package vendored into child repo

The bootstrap script SHALL download the local-tooling subset of the
`panopticon` Python package — the modules that Phase 2 skills and the Phase 3
finalization command invoke directly (`__init__.py`, `config.py`,
`providers.py`, `dependencies.py`, `docs.py`, `index.py`, and `init_repo.py`),
plus the local sync script, org-diagram link script, and recovery helper — from
the instance repo and write them to the child repo's `panopticon/` directory.
It SHALL create that directory if absent, so `python3 -m panopticon.docs`,
`python3 -m panopticon.init_repo`, `python3 -m panopticon.sync`, and
`python3 -m panopticon.org_diagram_link` all run immediately after Phase 1
without cloning the instance repo or configuring `PYTHONPATH`.

Modules used only by reusable GitHub Actions workflows that check out the
instance repo directly SHALL NOT be written to the child repository. Where a
vendored module imports another local `panopticon` module at runtime, that
dependency SHALL be included in the vendored subset.

Because the vendored subset and the instance repo's full package share the
same package name, a CI workflow that checks out both SHALL guarantee that
CI-only modules resolve from the instance repo rather than relying on
`PYTHONPATH` ordering alone.

#### Scenario: Local commands resolve all vendored dependencies after bootstrap

- **GIVEN** a freshly bootstrapped child repository with no instance-repo clone
- **WHEN** the user runs `python3 -m panopticon.docs render` or
  `python3 -m panopticon.init_repo --instance owner/instance`
- **THEN** imports required by those commands, including
  `panopticon.providers`, resolve from the child repository's vendored
  `panopticon/` directory

#### Scenario: Sync repairs a child repository missing the provider module

- **GIVEN** a previously bootstrapped child repository whose vendored tooling
  predates `providers.py`
- **WHEN** the user runs `python3 -m panopticon.sync`
- **THEN** the sync writes `panopticon/providers.py` from the instance and
  reports it as a created or updated tooling file

#### Scenario: CI-only modules remain excluded

- **WHEN** bootstrap or sync vendors the local-tooling subset
- **THEN** it includes only local commands and their runtime dependencies, and
  does not vendor CI-only modules such as `llm.py`, `drift.py`, `currency.py`,
  `merge.py`, `extraction.py`, `bootstrap.py`, or `parsers/`

### Requirement: Initialization finalization

A finalization command, distinct from the bootstrap script, SHALL validate the
agent-produced documentation and local index and write `panopticon/config.json`
only when validation passes. It SHALL adopt or accept the documentation
location, record it in config with the repository, instance, workflow ref, and
instance default branch, and verify organization-level CI prerequisites on a
report-only basis. Re-running finalization SHALL update configuration in place.

On every finalization attempt, including validation failure and successful
re-initialization, it SHALL write `panopticon-initialization-report.md` in the
child repository root before exiting. The report SHALL lead with the outcome,
then list each finding under exactly one ownership category: `Template/tooling`,
`Child repository`, or `Organization configuration`. Every finding SHALL state
the affected artifact or configuration location, what could not be verified or
what is wrong, and one concise next action. A report with no findings SHALL say
that initialization completed with no actionable issues. The report MUST NOT
include secret values, tokens, or environment-variable values.

#### Scenario: Validation fails with a durable child-repository remedy

- **WHEN** finalization finds missing documentation layers or an invalid local
  index
- **THEN** it does not write `panopticon/config.json`, writes the report before
  exiting, and places each validation finding under `Child repository` with the
  affected path and the command or skill needed before rerunning finalization

#### Scenario: Organization verification cannot run

- **WHEN** finalization cannot inspect organization Actions configuration
  because authentication or organization permission is unavailable
- **THEN** it writes a non-blocking `Organization configuration` report entry
  that names the required configuration, the organization settings location or
  verification command, and does not claim the configuration is absent

#### Scenario: Finalization succeeds with no actionable issues

- **WHEN** validation passes and organization prerequisite verification finds
  no issues
- **THEN** finalization writes `panopticon/config.json` and a concise report
  stating that initialization completed with no actionable issues

#### Scenario: Re-finalization refreshes the report

- **GIVEN** a child repository already has an initialization report
- **WHEN** finalization is run again after remediation
- **THEN** it overwrites the report with the current outcome and findings and
  does not leave duplicate report files
