# PR Evaluation Delta

## ADDED Requirements

### Requirement: Provider workflow caller contracts are checked before release

The template SHALL test the declared `workflow_call` input and secret contract
of each provider-specific reusable PR-evaluation workflow against its GitHub
expression references before release. A workflow that references an undeclared
caller input or secret SHALL fail deterministic repository validation rather
than relying on GitHub Actions to reject a caller with zero jobs.

#### Scenario: Provider workflow contract validation succeeds

- **WHEN** the repository validation suite examines every shipped
  provider-specific reusable PR-evaluation workflow
- **THEN** each workflow has declarations for every referenced caller input and
  secret, and the validation succeeds

#### Scenario: Provider workflow contract validation detects a startup defect

- **WHEN** a provider-specific reusable PR-evaluation workflow introduces a
  reference to an undeclared caller input or secret
- **THEN** repository validation fails and identifies the undeclared reference
