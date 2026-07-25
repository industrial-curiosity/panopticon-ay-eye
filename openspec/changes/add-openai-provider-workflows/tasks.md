# Direct OpenAI provider workflow tasks

## 1. Provider contract and runtime

- [x] 1.1 Add the trusted `openai` provider contract with its fixed reusable
  workflow, API-key and model names, fixed `https://api.openai.com/v1` endpoint,
  permissions, and deterministic revision inputs; expose no endpoint name.
- [x] 1.2 Allow the shared HTTP runtime to select `openai` while preserving the
  existing OpenAI-compatible Chat Completions request and response behavior.
- [x] 1.3 Make OpenAI preflight and operational failures identify OpenAI and
  retain the existing actionable missing-configuration recovery behavior.

## 2. OpenAI workflow entrypoints

- [x] 2.1 Add `configure-panopticon-openai.yml` as the correctly named LiteLLM
  configuration-workflow clone with a fixed `openai` identity and OpenAI-specific
  form labels and examples.
- [x] 2.2 Add `panopticon-pr-openai.yml` as the correctly named LiteLLM
  reusable workflow clone with fixed `PANOPTICON_LLM_PROVIDER=openai` and
  OpenAI-specific labels, summaries, and recovery output.
- [x] 2.3 Extend the shared configuration action and recovery formatter so
  OpenAI configuration, unconfigured-provider remediation, and stale-caller
  recovery use the selected fixed provider and its workflow names.

## 3. Bootstrap and verification

- [x] 3.1 Update bootstrap and generated caller wiring to select the trusted
  OpenAI reusable workflow and explicitly map the configured API key, model,
  instance token, budget variables, permissions, and contract revision, without
  an endpoint input or mapping.
- [x] 3.2 Extend unit and structural workflow tests for OpenAI provider
  validation, runtime selection, configuration, generated callers, recovery,
  and parity with LiteLLM behavior.
- [x] 3.3 Run the relevant unit and workflow test suites and
  `openspec validate add-openai-provider-workflows --strict`.

## 4. Documentation

- [x] 4.1 Update README.md and docs/spec.md to reflect the corrected
  GitHub-rate-limit waiting behavior and authentication guidance.
- [x] 4.2 Keep the setup guide concise while identifying the OpenAI path, fixed
  `https://api.openai.com/v1` endpoint, OpenAI Platform API key, and GitHub
  authentication needed for reliable installation; omit runtime tuning details.

## 5. GitHub API rate-limit retry bounds

- [x] 5.1 Remove the 60-second cap from GitHub-directed `Retry-After` and
  reset-time waits in the launcher, bootstrap, and sync clients, retaining
  fallback backoff and safe progress output.
- [x] 5.2 Add regression coverage that each affected GitHub API client honors
  long `Retry-After` and reset-time values without an early retry.
- [x] 5.3 Run the affected unit suites and
  `openspec validate add-openai-provider-workflows --strict`.
