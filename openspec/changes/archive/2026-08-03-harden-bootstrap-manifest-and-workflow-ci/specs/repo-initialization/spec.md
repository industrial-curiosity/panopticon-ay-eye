# Repository Initialization Specification Delta

## MODIFIED Requirements

### Requirement: Local tooling package vendored into child repo

The bootstrap script SHALL download the local-tooling subset of the
`panopticon` Python package from the versioned, data-only local-tooling
manifest at `panopticon/local-tooling.json` in the selected instance ref. The
manifest SHALL contain a supported positive `schema_version` and a non-empty
`modules` array of unique flat `.py` filenames. Bootstrap SHALL reject malformed
JSON, unsupported schema versions, duplicate names, paths containing separators
or traversal, and modules absent from that selected instance tree before it
writes a tooling file.

Bootstrap SHALL fetch the manifest and every listed module before writing any
listed module to the child repo's `panopticon/` directory. It SHALL create that
directory if absent, so `python3 -m panopticon.docs`,
`python3 -m panopticon.init_repo`, `python3 -m panopticon.sync`, and
`python3 -m panopticon.org_diagram_link` all run immediately after Phase 1
without cloning the instance repo or configuring `PYTHONPATH`.

Modules used only by reusable GitHub Actions workflows that check out the
instance repo directly SHALL NOT be listed or written to the child repository.
Where a vendored module imports another local `panopticon` module at runtime,
that dependency SHALL be included in the manifest. The bootstrap module SHALL
not require an imported or executable manifest module in order to start.

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

#### Scenario: Bootstrap uses the selected instance manifest

- **GIVEN** the selected instance ref contains a manifest that differs from
  the template checkout's local files
- **WHEN** bootstrap vendors local tooling
- **THEN** it fetches and validates that selected-ref manifest and writes only
  its listed modules

#### Scenario: Bootstrap stages tooling before writing

- **GIVEN** a selected instance manifest lists multiple local-tooling modules
- **WHEN** retrieval of a later listed module fails
- **THEN** bootstrap writes none of the listed modules

#### Scenario: CI-only modules remain excluded

- **WHEN** bootstrap or sync vendors the local-tooling subset
- **THEN** it includes only manifest-listed local commands and their runtime
  dependencies, and does not vendor CI-only modules such as `llm.py`,
  `drift.py`, `currency.py`, `merge.py`, `extraction.py`, `bootstrap.py`, or
  `parsers/`

### Requirement: Child sync uses the explicit local-tooling manifest

Child bootstrap and child resource sync SHALL manage the same explicit,
versioned, data-only instance-owned local-tooling manifest at
`panopticon/local-tooling.json`. Bootstrap and resource sync SHALL download the
manifest from the selected instance ref on every run and SHALL NOT use a child
copy to select modules. They SHALL validate the manifest, fetch every listed
module before writing any listed module, and fetch, preview, and overwrite only
manifest-listed modules. They SHALL NOT delete existing child files outside the
manifest.

For Python source paths under `panopticon/` outside the manifest, sync SHALL
ignore child configuration, indexes, `.gitignore`, and bytecode. It SHALL report
an advisory instance-excluded warning for paths also present in the selected
instance tree and an advisory child-only-and-unknown warning for all other
candidates. These warnings SHALL preserve every candidate and SHALL not alter
sync's exit status.

#### Scenario: Sync encounters CI-only module

- **WHEN** the instance tree contains a CI-only `panopticon/` module outside
  the local-tooling manifest
- **THEN** child sync reports it as instance-excluded and leaves it unchanged

#### Scenario: Sync refreshes child-safe tooling

- **WHEN** a manifest-listed module changes in the instance
- **THEN** preview reports it and apply refreshes it in the child repository

#### Scenario: Child has a stale manifest copy

- **WHEN** a child repository contains an older local-tooling manifest
- **THEN** bootstrap and resource sync use the manifest downloaded from the
  selected instance ref to select modules

#### Scenario: Child has an unmanaged module

- **WHEN** a child repository contains a `panopticon/` file outside the
  local-tooling manifest
- **THEN** child sync reports it as child-only and unknown, then leaves it
  unchanged

#### Scenario: Child state is not a tooling candidate

- **GIVEN** a child contains `panopticon/config.json`, `panopticon/index.json`,
  `.gitignore`, or bytecode
- **WHEN** child resource sync runs
- **THEN** sync emits no unmanaged-tooling warning for that state file
