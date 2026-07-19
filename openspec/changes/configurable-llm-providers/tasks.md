# Configurable LLM providers tasks

## 1. Provider configuration model

- [ ] 1.1 Add the closed LiteLLM/Bedrock provider registry with trusted workflow paths, logical
  requirements, default secret/variable names, permissions, and contract version metadata.
- [ ] 1.2 Extend org-config parsing with optional unconfigured LLM state, strict provider resolution,
  configured-name validation, canonical serialization, and deterministic revision hashing.
- [ ] 1.3 Remove the implicit provider from the template `panopticon.config.json` and add config tests for
  unconfigured, valid, unknown-provider, malformed-name, and revision-change cases.

## 2. Instance configuration workflow

- [ ] 2.1 Add an importable, standard-library instance-configuration module that validates dispatch inputs
  and updates only the provider contract in `panopticon.config.json` without accepting credential values.
- [ ] 2.2 Add `.github/workflows/configure-panopticon.yml` with the provider sentinel, provider-specific name
  defaults, early input validation, contents-write commit behavior, and end-to-end failure summaries.
- [ ] 2.3 Test deterministic config updates, no-op reruns, invalid input, secret-value exclusion, commit/push
  failure reporting, and the direct Actions URL plus equivalent `gh workflow run` instructions.

## 3. Provider-aware child bootstrap

- [ ] 3.1 Make org-config fetching preserve and report access, transport, decode, and schema failures instead
  of returning an empty object.
- [ ] 3.2 Validate the complete provider contract and selected remote workflow at the effective
  `workflow_ref` before bootstrap prompts, downloads, or writes any child path.
- [ ] 3.3 Replace matching local/remote workflow tuples with logical caller definitions and generate the
  stable local PR caller for only the selected provider using explicit inputs, secrets, permissions, and
  configuration revision.
- [ ] 3.4 Resolve merge and PR-close instance-token mappings from the same configured name while preserving
  their provider-independent reusable workflow targets.
- [ ] 3.5 Make prerequisite reporting consume provider-resolved secret and variable names, including complete
  manual verification URLs and commands when org-level APIs cannot be queried.
- [ ] 3.6 Add atomicity and caller-generation tests covering unconfigured instances, both providers,
  workflow-ref mismatch, custom names, explicit mappings, absence of `secrets: inherit`, and no partial
  child writes on every validation failure.

## 4. Shared runtime and provider adapters

- [ ] 4.1 Extract the current OpenAI-compatible HTTP behavior behind a LiteLLM adapter without changing its
  request shape, retries, parsing, exceptions, or structured-response correction loop.
- [ ] 4.2 Add the Bedrock Converse adapter with lazy injected client construction, system/conversation and
  inference mapping, text response parsing, and provider error classification into existing runtime errors.
- [ ] 4.3 Add centralized adapter preflight, including Bedrock Converse capability checks that report the
  resolved SDK version and import path before any LLM-dependent check runs.
- [ ] 4.4 Add and justify a pinned CI-only AWS SDK dependency in the single requirements file, keeping it out
  of child-vendored tooling and LiteLLM/local execution paths.
- [ ] 4.5 Expand runtime tests with injected LiteLLM HTTP and Bedrock clients for provider selection,
  request/response mapping, retries, errors, preflight, structured correction, and lazy dependency loading.

## 5. Independent provider PR workflows

- [ ] 5.1 Create `panopticon-pr-litellm.yml` with canonical workflow-call inputs/secrets and the complete
  existing PR evaluation contract, without AWS permissions or dependency setup.
- [ ] 5.2 Create `panopticon-pr-bedrock.yml` with canonical workflow-call inputs/secrets, caller-compatible
  `id-token: write`, AWS OIDC configuration, isolated `actions/setup-python` dependency installation,
  preflight, and the complete existing PR evaluation contract.
- [ ] 5.3 Convert the instance-side generic `panopticon-pr.yml` into a legacy guard that checks out the child,
  resolves its recorded instance, and fails with complete instance-configuration and child-bootstrap
  remediation instead of a workflow-load error.
- [ ] 5.4 Add early provider-workflow validation for empty canonical secrets/inputs and mismatched config
  revisions before instance checkout or LLM work.
- [ ] 5.5 Add workflow parity and contract tests that validate required inputs, secrets, permissions, common
  PR phases, timeout mapping, independent-check behavior, reporting, gating, and provider-only setup.

## 6. Recovery and migration behavior

- [ ] 6.1 Centralize user-facing unconfigured/stale remediation rendering for terminal and GitHub step-summary
  contexts without exposing credential values.
- [ ] 6.2 Ensure unconfigured failures print the resolved `Configure Panopticon` Actions URL, ordered console
  steps, equivalent `gh workflow run`/run-watch commands, and the resolved default branch.
- [ ] 6.3 Ensure stale and renamed-secret failures print the exact one-line command
  `curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='<owner/repo>' python3`
  plus child-root, review, commit, push, and workflow-rerun instructions.
- [ ] 6.4 Add exact-output tests for missing provider, legacy caller, changed provider, changed name, revision
  mismatch, empty old instance-token mapping, private instance, and custom workflow-ref recovery paths.
- [ ] 6.5 Implement and test the staged compatibility rollout so configuration support lands before strict
  enforcement and old provider workflows/secrets remain usable until child callers are regenerated.

## 7. Architecture and documentation hygiene

- [ ] 7.1 Update the Panopticon architecture and Python-tooling skills to permit only justified, pinned,
  CI-only SDKs inside built-in provider adapters while preserving the stdlib-only child/local contract.
- [ ] 7.2 Reconcile `docs/action-plans/llm-provider-plugins.md`, `ci-dependency-isolation.md`,
  `oidc-caller-permissions.md`, `runtime-preflight.md`, `configurable-instance-token.md`, and
  `docs/explore/workflow-customization.md` with the accepted instance-configured, separate-workflow design.
- [ ] 7.3 Update `docs/setup-guide.md`, `docs/testing.md`, `docs/planned-work.md`, and `CHANGELOG.md` with both
  provider setup paths, exact console/CLI/bootstrap recovery, safe secret-name rotation, migration ordering,
  and test coverage.
- [ ] 7.4 Run the full unit suite, strict OpenSpec validation, workflow validation, and markdown lint; fix all
  in-scope failures and verify no archived OpenSpec history was rewritten.
- [ ] Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
