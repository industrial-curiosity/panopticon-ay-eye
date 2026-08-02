# Tooling Currency Delta

## ADDED Requirements

### Requirement: Tooling-currency identifies unmanaged Python tooling

The advisory tooling-currency check SHALL identify Python source paths under a
child's `panopticon/` directory that are outside the instance-owned
local-tooling manifest. It SHALL ignore child configuration, indexes,
`.gitignore`, and bytecode. A candidate also present in the instance checkout
but excluded from the manifest SHALL be reported as instance-excluded; every
other candidate SHALL be reported as child-only and unknown. These findings
SHALL remain non-blocking `::warning::` output and SHALL not alter files.

#### Scenario: Instance-excluded module is advisory

- **GIVEN** a child contains `panopticon/llm.py` and the instance checkout
  contains the same path outside the local-tooling manifest
- **WHEN** tooling-currency runs in the PR workflow
- **THEN** it emits a non-blocking warning classifying the module as
  instance-excluded

#### Scenario: Child-only module is advisory

- **GIVEN** a child contains `panopticon/legacy_child_module.py` that is absent
  from the instance checkout and the local-tooling manifest
- **WHEN** tooling-currency runs in the PR workflow
- **THEN** it emits a non-blocking warning classifying the module as child-only
  and unknown

#### Scenario: Child state is excluded from candidate detection

- **GIVEN** a child contains `panopticon/config.json`, `panopticon/index.json`,
  `.gitignore`, or bytecode
- **WHEN** tooling-currency runs in the PR workflow
- **THEN** it emits no unmanaged-tooling warning for that state file
