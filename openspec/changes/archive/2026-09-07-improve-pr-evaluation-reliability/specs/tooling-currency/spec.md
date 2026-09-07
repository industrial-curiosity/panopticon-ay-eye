# Tooling currency delta

## MODIFIED Requirements

### Requirement: Tooling-currency checks are always advisory

The workflow-ref alignment and skills/tooling drift checks SHALL remain advisory. Neither check SHALL have an entry in the org config's check-type/gating mechanism, and neither SHALL ever fail the PR workflow, regardless of org configuration. When one or more findings exist, the check SHALL emit exactly one non-blocking `::warning::` annotation naming the total finding count and the managed-resource sync recovery action. It SHALL write each individual finding to the GitHub step summary. They SHALL NOT be included in the PR workflow's combined TL;DR report, since that report's contract is a list of actions a developer must take before merge, and nothing a tooling-currency check finds is required before merge.

#### Scenario: Drifted tooling never fails the workflow

- **GIVEN** the skills and tooling drift check finds every vendored module out of date
- **WHEN** the PR workflow's gating step runs
- **THEN** the workflow succeeds regardless — this finding has no bearing on the exit status

#### Scenario: Multiple findings produce one annotation

- **GIVEN** workflow-ref alignment and skills/tooling comparison produce four findings
- **WHEN** tooling currency reports the result
- **THEN** it emits one warning naming four findings and the sync recovery action, and the step summary lists all four findings

#### Scenario: Tooling-currency findings are absent from the combined report

- **GIVEN** the workflow-ref alignment check and the skills/tooling drift check both find drift
- **WHEN** the PR workflow's combined TL;DR report is built
- **THEN** neither finding appears in that report
