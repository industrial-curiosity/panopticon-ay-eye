# LLM Provider Configuration Delta

## ADDED Requirements

### Requirement: Bedrock evaluation has no LiteLLM caller dependency

The Bedrock reusable PR-evaluation workflow SHALL use only its declared
Bedrock provider contract for caller inputs and secrets. It SHALL NOT reference
LiteLLM API-key or endpoint caller configuration.

#### Scenario: Bedrock caller supplies its declared contract

- **WHEN** a child caller invokes the Bedrock reusable PR-evaluation workflow
  with the configured Bedrock credential mode, model, instance token, and
  budget values
- **THEN** GitHub Actions accepts the reusable-workflow contract and creates
  the evaluation job without requiring a LiteLLM API-key or endpoint value
