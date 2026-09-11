# Implementation Tasks

## 1. Regression Coverage

- [x] 1.1 Add a finalization regression test for an advisory child feature
  receipt and helper without `features/manifest.json`, including the viable
  continuation text.

## 2. Child Initialization Recovery

- [x] 2.1 Update the init skill and finalization report to send feature
  remediation through the installed skill and child-side finalization, never
  the registry-dependent feature-check CLI.
- [x] 2.2 Run the focused initialization and feature-lifecycle tests.

## 3. Documentation Review

- [x] 3.1 Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes introduced by this change.

## 4. Template Workflow Syntax Validation

- [x] 4.1 Add canonical-template PR validation that parses every workflow YAML
  file before reusable-workflow contract validation and reports actionable
  syntax failures.
- [x] 4.2 Add regression coverage for the workflow-syntax validation step and
  run the focused workflow tests, full Python suite, and strict OpenSpec
  validation.
