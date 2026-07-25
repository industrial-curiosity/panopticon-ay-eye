# Add direct OpenAI provider workflows

## Why

The current OpenAI-compatible workflow is labelled LiteLLM even when it calls
OpenAI's API directly. This makes direct OpenAI configuration look as though it
requires a LiteLLM proxy and obscures the provider selected by an instance.

## What Changes

- Add an explicit `openai` provider contract alongside `litellm` and Bedrock.
- Add correctly named OpenAI configuration and reusable PR-evaluation workflows
  that retain the LiteLLM workflow's request, authentication, retry, and
  validation behavior.
- Wire provider selection, child bootstrap, recovery guidance, and
  documentation to expose OpenAI as a separate fixed provider.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `llm-provider-configuration`: support an explicit OpenAI contract and
  provider-specific configuration workflow.
- `agent-runtime`: permit the existing OpenAI-compatible chat-completions
  transport to run under the OpenAI provider identity.
- `pr-evaluation`: provide a distinct reusable OpenAI PR-evaluation workflow.
- `repo-initialization`: generate child callers and recovery guidance for the
  selected OpenAI workflow.

## Impact

The provider registry, configuration action and workflows, bootstrap and
recovery code, workflow tests, and setup documentation will gain an `openai`
provider. No new runtime dependency or API transport is required.
