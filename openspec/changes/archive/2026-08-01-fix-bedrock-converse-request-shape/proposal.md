# Fix Bedrock Converse Request Shape

## Why

The Bedrock adapter includes `inferenceConfig.temperature` in every Converse
request. The configured Claude model rejects that parameter, so an otherwise
valid provider configuration fails during PR evaluation.

The adapter must send the smallest provider-supported request shape by default
and prevent unsupported optional fields from returning unnoticed.

## What Changes

- Stop sending the `inferenceConfig.temperature` field in Bedrock Converse
  requests.
- Preserve provider-neutral `chat()` callers while intentionally ignoring the
  shared temperature argument for Bedrock until support is explicitly added.
- Update Bedrock adapter tests to assert the exact native request shape.
- Document the request-shape constraint in the test/process documentation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-runtime`: Bedrock Converse requests must omit unsupported inference
  parameters while preserving the shared prompting, retry, and error contract.

## Impact

This change affects `panopticon/llm.py`, its unit tests, and test-process
documentation. It changes no provider configuration, credentials, child
tooling, or LiteLLM/OpenAI request behavior.
