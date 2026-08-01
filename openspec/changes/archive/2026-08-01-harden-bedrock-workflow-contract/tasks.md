# Implementation Tasks

## 1. Workflow Repair

- [x] 1.1 Remove the undeclared LiteLLM API-key and endpoint references from the Bedrock reusable PR workflow.
- [x] 1.2 Add a focused workflow assertion proving Bedrock has no LiteLLM caller dependency.

## 2. Deterministic Contract Validation

- [x] 2.1 Add an importable standard-library validator for `workflow_call` input and secret declarations and GitHub expression references.
- [x] 2.2 Add unit coverage for valid provider workflows and undeclared input and secret references.

## 3. Maintainer Guidance and Verification

- [x] 3.1 Document the zero-job reusable-workflow contract failure and its local validation recovery path.
- [x] 3.2 Run focused and full test suites, strict OpenSpec validation, and Markdown structure checks.
