# Repo Initialization Delta

## ADDED Requirements

### Requirement: Child sync warns about unmanaged Python tooling

Child resource sync SHALL identify Python source paths under `panopticon/` that
are outside the instance-owned local-tooling manifest. It SHALL ignore child
configuration, indexes, `.gitignore`, and bytecode. For each candidate that is
also present in the selected instance tree but excluded from the manifest, sync
SHALL emit an advisory warning that it is instance-excluded. For every other
candidate, sync SHALL emit an advisory warning that it is child-only and
unknown. Sync SHALL preserve every candidate and SHALL not change its exit
status because of these warnings.

#### Scenario: Child retains an instance-excluded module

- **GIVEN** a child contains `panopticon/llm.py`, the selected instance tree
  also contains that file, and the local-tooling manifest excludes it
- **WHEN** child resource sync previews or applies updates
- **THEN** sync warns that the file is instance-excluded and leaves it unchanged

#### Scenario: Child retains an unknown module

- **GIVEN** a child contains `panopticon/legacy_child_module.py` that is absent
  from both the manifest and the selected instance tree
- **WHEN** child resource sync previews or applies updates
- **THEN** sync warns that the file is child-only and unknown and leaves it
  unchanged

#### Scenario: Child state is not a tooling candidate

- **GIVEN** a child contains `panopticon/config.json`, `panopticon/index.json`,
  `.gitignore`, or bytecode
- **WHEN** child resource sync runs
- **THEN** sync emits no unmanaged-tooling warning for that state file
