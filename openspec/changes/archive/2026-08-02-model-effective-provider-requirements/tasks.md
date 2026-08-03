# Implementation Tasks

## 1. Trusted effective-value contract

- [x] 1.1 Extend the provider registry and `llm` configuration validation with optional-variable metadata, non-secret instance defaults, declared template defaults, and a contract revision that changes when any effective-value source changes.
- [x] 1.2 Add one deterministic runtime effective-value resolver that selects organization Actions input, fixed instance-action output, instance configuration default, then workflow default, while rejecting unresolved and required defaulted values without logging values; resolve job timeout in generated callers because GitHub evaluates it before steps.
- [x] 1.3 Add the fixed reviewed instance default-resolver action contract at `.github/actions/panopticon-provider-defaults/action.yml`, with closed outputs for optional logical names and no credential inputs or arbitrary action selection.

## 2. Caller and reusable-workflow resolution

- [x] 2.1 Update generated callers and provider reusable workflows to retain raw organization values, embed validated instance job-timeout defaults when needed, pass validated contract metadata, invoke only the fixed resolver action for runtime values, and apply resolved values before provider preflight.
- [x] 2.2 Update provider workflow summaries and stale-caller recovery to report each logical value's source label, required status, and exact safe remediation without exposing values or credentials.

## 3. Bootstrap and finalization reporting

- [x] 3.1 Update bootstrap and organization prerequisite checks to distinguish required missing names, values supplied by each trusted default source, and unresolved optional values without falsely reporting defaulted values as missing.
- [x] 3.2 Update finalization reports and recovery formatting with the same source labels, configuration URLs or commands, and child-bootstrap remediation for changed contract revisions.

## 4. Regression coverage

- [x] 4.1 Add provider-contract and configuration tests for valid optional names, invalid names, source precedence, contract-revision changes, empty organization collections, and absent effective defaults.
- [x] 4.2 Add caller and reusable-workflow tests for raw input preservation, fixed-action path/output validation, required-value failures, source-safe summaries, and provider preflight ordering.
- [x] 4.3 Add bootstrap, initialization, and finalization tests proving defaulted optional values are not reported missing while required values and missing defaults remain actionable.

## 5. Integrator documentation

- [x] 5.1 Write a provider-configuration guide with a provider-specific required/optional/source table, the precedence order, a simplest-path organization-variable walkthrough, and a separate fixed-action walkthrough with validation and recovery commands.
- [x] 5.2 Update workflow-dispatch descriptions, setup and recovery documentation, and testing guidance so every organization integration path identifies ownership, configured names, expected evidence, and the next action.
- [x] 5.3 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.

## 6. Verification

- [x] 6.1 Run focused provider, caller, bootstrap, initialization, and workflow tests; the full Python suite; strict OpenSpec validation; and Markdown structure checks.
