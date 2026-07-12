## ADDED Requirements

### Requirement: Tooling-currency PR check

The PR workflow SHALL run the workflow-ref alignment check and the skills/tooling drift check
(tooling-currency capability) after the instance repo is checked out, using that same checkout —
no additional network calls, no GitHub API usage, no LLM involvement. These checks SHALL run for
every initialized repo's PR, independent of every other check's outcome, and SHALL NOT participate
in the org config's gating mechanism or the PR workflow's combined TL;DR report (tooling-currency
capability: "Tooling-currency checks are always advisory").

#### Scenario: Tooling-currency checks run alongside the other PR checks

- **WHEN** a PR workflow runs for an initialized repo
- **THEN** the workflow-ref alignment check and the skills/tooling drift check both run after the
  instance repo checkout step, independent of whether doc-drift, index-currency, diagram-existence,
  or pre-merge simulation found problems

#### Scenario: Tooling-currency drift does not affect the workflow's outcome

- **GIVEN** the workflow-ref alignment check and the skills/tooling drift check both find drift
- **WHEN** the PR workflow's final gating step runs
- **THEN** the workflow's pass/fail outcome is unaffected by either finding
