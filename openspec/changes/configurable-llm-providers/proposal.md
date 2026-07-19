# Configurable LLM providers

## Why

Panopticon currently assumes every organization exposes a LiteLLM-compatible endpoint under fixed
GitHub Actions secret and variable names. Organizations whose approved CI access is native Amazon
Bedrock through OIDC must fork the shared runtime and workflows, while a newly created instance can
appear configured even though no usable LLM provider was deliberately selected.

## What Changes

- Add an instance configuration workflow that requires the maintainer to select an LLM provider and
  persists only provider choice plus configurable secret and variable *names* in
  `panopticon.config.json`; secret values never enter the file or workflow inputs.
- Ship LiteLLM and Amazon Bedrock as separate, first-class reusable PR workflows. The template selects
  neither provider by default.
- Make the child bootstrap installer read and validate the instance provider contract before writing
  any child files, then generate the stable local PR caller to reference only the selected provider
  workflow with explicit inputs, secret mappings, and permissions.
- Add a configuration revision to generated callers so provider or name changes fail loudly until the
  child bootstrap installer is rerun.
- Replace fixed LLM prerequisite names with provider-resolved requirements while preserving bounded
  timeout and retry behavior.
- Add complete recovery guidance for unconfigured instances and stale callers: a direct GitHub Actions
  console URL, equivalent `gh workflow run` command, and an exact one-line child bootstrap command with
  the instance slug embedded.
- Keep a legacy PR workflow guard that directs existing callers to configure the instance and rerun
  bootstrap instead of failing at workflow load time.
- **BREAKING**: instances no longer inherit LiteLLM as an implicit default. They must run the instance
  configuration workflow and regenerate child callers before provider-backed PR evaluation can run.

## Capabilities

### New Capabilities

- `llm-provider-configuration`: Instance-owned provider selection, provider-specific secret and
  variable name contracts, configuration workflow behavior, revisioning, and recovery instructions.

### Modified Capabilities

- `agent-runtime`: Replace the single LiteLLM transport assumption with provider-specific runtimes
  behind the existing shared prompting, retry, validation, and error contracts.
- `repo-initialization`: Require provider configuration before child bootstrap writes files and generate
  the selected provider's caller contract with explicit mappings and exact remediation commands.
- `pr-evaluation`: Route PR evaluation through separate provider workflows and fail stale or legacy
  callers with actionable bootstrap recovery instructions.
- `llm-timeout-configuration`: Resolve configurable Actions variable names into the same bounded request
  and job budgets instead of requiring fixed variable names.

## Impact

The change affects `panopticon.config.json`, `panopticon/config.py`, the bootstrap and initialization
tooling, reusable and generated GitHub Actions workflows, the CI-only LLM runtime, prerequisite checks,
tests, setup documentation, architecture guidance, and planned-work/exploration documents. Native
Bedrock support introduces a pinned CI-only AWS SDK dependency and OIDC permission path; child-vendored
Python tooling and local agent flows remain standard-library-only and require no Panopticon LLM secrets.
