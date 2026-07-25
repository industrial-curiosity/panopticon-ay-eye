# Default optional LLM environment variables tasks

## 1. Provider workflow defaulting

- [x] 1.1 Apply the documented fallback expressions for timeout, transport
  attempts, and correction attempts to every LLM-invoking step environment in
  the LiteLLM reusable PR workflow.
- [x] 1.2 Apply the same fallback expressions to every LLM-invoking step
  environment in the Bedrock reusable PR workflow.

## 2. Regression coverage

- [x] 2.1 Extend provider-workflow tests to verify every LLM-invoking step in
  both workflows supplies the documented request-budget defaults when optional
  inputs are absent.
- [x] 2.2 Run the focused provider-workflow tests and the full relevant test
  suite to verify valid and invalid overrides retain their existing behavior.

## 3. Documentation

- [x] 3.1 Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes introduced by this change.
