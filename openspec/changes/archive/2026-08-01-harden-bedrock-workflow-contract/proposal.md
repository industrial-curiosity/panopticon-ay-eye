# Harden Bedrock Workflow Contract

## Why

The Bedrock reusable workflow references LiteLLM-only caller inputs and secrets
that it does not declare. GitHub Actions rejects this contract before creating
any jobs, leaving adopters with an opaque zero-job failure rather than an
actionable evaluation result.

The template must prevent this class of release-blocking workflow defect across
all provider-specific reusable workflows, not merely repair the current
Bedrock instance.

## What Changes

- Remove the undeclared LiteLLM endpoint and API-key references from the Bedrock
  PR-evaluation workflow.
- Add a deterministic repository check that compares reusable-workflow
  `workflow_call` input and secret declarations with every corresponding GitHub
  expression reference.
- Cover each shipped provider workflow with regression tests, including the
  invalid undeclared-reference case and valid Bedrock isolation from LiteLLM
  configuration.
- Document the zero-job workflow-contract failure mode and the template's
  validation safeguard for maintainers.

## Capabilities

### New Capabilities

- `reusable-workflow-contract-validation`: Detect undeclared caller input and
  secret references in template-owned reusable GitHub Actions workflows before
  they are released.

### Modified Capabilities

- `pr-evaluation`: Provider-specific PR-evaluation workflows must expose only
  their declared caller contract and must be statically checked for declaration
  and reference consistency.
- `llm-provider-configuration`: Bedrock evaluation must remain independent of
  LiteLLM endpoint and API-key caller configuration.

## Impact

This change affects the Bedrock reusable workflow, provider-workflow tests, a
new deterministic workflow-contract validation module or test helper, and
maintainer documentation. It adds no runtime dependency, changes no credential
values, and does not alter non-Bedrock provider request behavior.
