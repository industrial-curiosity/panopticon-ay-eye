# Direct OpenAI provider workflow design

## Context

Panopticon already sends OpenAI-compatible `/chat/completions` requests through
the LiteLLM adapter. The adapter can call `https://api.openai.com/v1` directly,
but a user selecting that configuration is represented as `litellm` in the
instance contract, generated child caller, workflow name, and recovery output.

The provider registry is the trusted boundary for selectable workflow paths,
permissions, logical Actions names, and dependency contracts. Configuration
workflows persist only logical Actions names; child bootstrap reads that trusted
contract and writes an explicit caller.

## Goals / Non-Goals

**Goals:**

- Add an explicit `openai` provider with OpenAI-labelled configuration and
  reusable PR-evaluation workflows.
- Preserve the existing stdlib HTTP request shape, bearer authentication,
  retry budget, validation, gating, and explicit child mapping behavior.
- Keep OpenAI and LiteLLM independently selectable so existing LiteLLM proxy
  instances need no migration.

**Non-Goals:**

- Replace the Chat Completions transport with the Responses API.
- Add an OpenAI SDK, another credential mode, or provider-specific request
  parameters.
- Infer an endpoint, silently migrate an existing instance, or change local
  agent flows.

## Decisions

### Register OpenAI as a separate fixed provider

Add `openai` to the trusted provider registry using the same logical API-key,
model, retry-budget, and instance-token names as the LiteLLM contract, but a
fixed `https://api.openai.com/v1` endpoint and its own configuration and PR
workflow paths. The configuration
workflow fixes `provider: openai`; no dispatch input can select another
provider or workflow path.

This makes the selected service visible in Actions, generated callers, error
messages, and recovery instructions while retaining the security boundary that
prevents instance configuration from redirecting a reusable workflow.

Alternative considered: rename the LiteLLM provider. Rejected because it would
misrepresent proxy-backed instances and make existing contracts and callers
stale without a migration path.

### Clone the LiteLLM workflow behavior under OpenAI names

Create `configure-panopticon-openai.yml` and `panopticon-pr-openai.yml` as
correctly named clones of their LiteLLM counterparts. They use the same shared
configuration action and canonical inputs, but fix the OpenAI provider identity
and use OpenAI labels in workflow names, summaries, preflight output, and
recovery guidance. They do not expose an endpoint input or environment variable:
the OpenAI endpoint is always `https://api.openai.com/v1`. The setup guide
documents that fixed endpoint and an OpenAI Platform API key as the secret value.

Alternative considered: parameterize one generic HTTP workflow. Rejected because
fixed, provider-specific entrypoints are a settled architecture rule and are
safer to audit.

### Reuse the existing HTTP adapter with provider-aware identity

Permit `LLMClient.from_env` to select `openai` and construct the existing
OpenAI-compatible adapter. Parameterize its provider identity only where it is
reported by preflight and operational errors; keep payload and response parsing
identical. This avoids a dependency and prevents divergence between direct
OpenAI and proxy behavior.

### Honor GitHub API retry waits and recommend authentication

GitHub-provided rate-limit timing is authoritative: the launcher, bootstrap,
and sync clients honor `Retry-After` and `X-RateLimit-Reset` without a local
cap, so they do not retry while GitHub is still limiting the request. When
GitHub provides neither signal, the existing exponential fallback remains.

Installation documentation recommends GitHub authentication for public as well
as private instances. This is the user-controlled way to obtain GitHub's
authenticated API quota; the documentation names supported credential sources
without asking users to place a token value in a command.

## Risks / Trade-offs

- Workflow clones can drift from LiteLLM behavior → structural tests compare
  their provider-specific wiring and shared evaluation semantics.
- Users may supply a ChatGPT/Codex login credential instead of an API key →
  configuration and docs explicitly require an OpenAI Platform API key.
- Existing callers cannot switch providers automatically → changing to OpenAI
  requires running its configuration workflow and rerunning child bootstrap,
  which updates the deterministic contract revision.

## Migration Plan

1. Release the template with the OpenAI contract and both workflows.
2. Existing LiteLLM instances remain unchanged.
3. An instance that wants direct OpenAI runs **Configure Panopticon — OpenAI**,
   configures the reported Actions secret and variables, then reruns child
   bootstrap to write OpenAI callers.
4. Reverting to LiteLLM uses the existing LiteLLM configuration workflow and
   another child-bootstrap run.

## Open Questions

None.
