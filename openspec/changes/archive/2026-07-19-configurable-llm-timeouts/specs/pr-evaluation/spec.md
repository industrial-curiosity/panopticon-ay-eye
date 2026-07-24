# PR evaluation timeout configuration changes

## ADDED Requirements

### Requirement: Bounded PR-evaluation job duration

The reusable PR-evaluation workflow SHALL set an explicit timeout for its
evaluate job from the optional org-level Actions variable
`PANOPTICON_LLM_JOB_TIMEOUT_MINUTES`, using 20 minutes when the variable is
unset. The setup guide SHALL document that the variable accepts a whole number
from 10 through 60 and is evaluated by GitHub Actions before the job starts.

#### Scenario: Default evaluate-job duration

- **WHEN** the PR-evaluation workflow runs without
  `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES`
- **THEN** GitHub Actions terminates the evaluate job after 20 minutes if it has
  not completed

#### Scenario: Configured evaluate-job duration

- **WHEN** the organization sets `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES` to a valid
  whole number from 10 through 60
- **THEN** GitHub Actions uses that number as the evaluate job timeout in
  minutes
