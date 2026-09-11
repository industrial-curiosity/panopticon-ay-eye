# Template Validation Scope Delta

## MODIFIED Requirements

### Requirement: Template validation is scoped to the canonical repository

The template validation workflow SHALL create its validation job only when
`github.repository` exactly identifies the canonical Panopticon template
repository. It SHALL not check out code or run validation when the workflow
file exists in a configured instance repository.

Before reusable-workflow contract validation or Python tests, the validation
job SHALL parse every `.yml` and `.yaml` file under `.github/workflows/`. If a
file has invalid YAML syntax, the job SHALL fail and write the file path,
parser reason, and line number to the job summary.

#### Scenario: Canonical template push runs validation

- **WHEN** a push, pull request, or manual dispatch runs the workflow in the
  canonical template repository
- **THEN** GitHub Actions creates the validation job and runs workflow-syntax
  validation, contract validation, and the Python test suite

#### Scenario: Malformed template workflow is proposed

- **GIVEN** a pull request in the canonical template repository changes a
  workflow file to invalid YAML
- **WHEN** template validation runs
- **THEN** the validation job fails before contract validation and Python tests
  and its summary identifies the invalid file, parser reason, and line number

#### Scenario: Configured instance retains the workflow

- **WHEN** a configured instance repository contains the template validation
  workflow and receives a push, pull request, or manual dispatch
- **THEN** GitHub Actions skips the validation job without running checkout or
  workflow validation

### Requirement: Template-validation behavior is regression-tested

The template repository SHALL include deterministic tests that verify the
canonical-repository guard, the guarded placement of the template test suite,
and the workflow-syntax validation step.

#### Scenario: Guard or syntax validation is removed or weakened

- **WHEN** the template-validation job no longer uses the exact canonical
  repository guard or no longer parses every workflow YAML file before its
  remaining checks
- **THEN** the deterministic workflow tests fail
