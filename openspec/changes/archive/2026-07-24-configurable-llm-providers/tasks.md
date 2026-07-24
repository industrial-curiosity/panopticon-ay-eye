# Configurable LLM providers tasks

## 1. Provider configuration model

- [x] 1.1 Add the closed LiteLLM/Bedrock provider and credential-mode registry with trusted workflow/action
  paths, logical requirements, default secret/variable names, permissions, and contract version metadata.
- [x] 1.2 Extend org-config parsing with optional unconfigured LLM state, strict provider and credential-mode
  resolution, configured-name validation, canonical serialization, and deterministic revision hashing.
- [x] 1.3 Remove the implicit provider from the template `panopticon.config.json` and add config tests for
  unconfigured, valid, unknown-provider, malformed-name, and revision-change cases.

## 2. Instance configuration workflow

- [x] 2.1 Add an importable, standard-library instance-configuration module that validates dispatch inputs
  and updates only the provider and credential-mode contract in `panopticon.config.json` without accepting
  credential values.
- [x] 2.2 Add `.github/workflows/configure-panopticon.yml` with clear labels and examples for every
  non-obvious dispatch field, the provider and trusted Bedrock credential-mode choices, provider-specific
  name defaults, separate optional bounded-budget variable-name inputs, early input validation,
  checked-out workspace import-path setup, contents-write commit behavior, and end-to-end validation,
  persistence, and recovery failure summaries.
- [x] 2.3 Test deterministic config updates, no-op reruns, invalid input, secret-value exclusion, clear
  field labels/examples, credential-mode validation, separate optional bounded-budget inputs and defaults,
  commit/push failure reporting, and the direct Actions URL plus equivalent `gh workflow run` instructions.

## 3. Provider-aware child bootstrap

- [x] 3.1 Make org-config fetching preserve and report access, transport, decode, and schema failures instead
  of returning an empty object.
- [x] 3.2 Validate the complete provider and credential-mode contract, selected remote workflow, and fixed
  instance credential action when required at the effective `workflow_ref` before bootstrap prompts,
  downloads, or writes any child path.
- [x] 3.3 Replace matching local/remote workflow tuples with logical caller definitions and generate the
  stable local PR caller for only the selected provider using explicit inputs, secrets, credential-mode
  mappings, permissions, and configuration revision.
- [x] 3.4 Resolve merge and PR-close instance-token mappings from the same configured name while preserving
  their provider-independent reusable workflow targets and actionable summaries for explicit shared-workflow
  failures.
- [x] 3.5 Make prerequisite reporting consume provider- and credential-mode-resolved secret and variable
  names, including complete manual verification URLs and commands when org-level APIs cannot be queried.
- [x] 3.6 Add atomicity and caller-generation tests covering unconfigured instances, both providers and
  Bedrock credential modes, workflow/action absence, custom names, explicit mappings, absence of
  `secrets: inherit`, and no partial child writes on every validation failure.

## 4. Shared runtime and provider adapters

- [x] 4.1 Extract the current OpenAI-compatible HTTP behavior behind a LiteLLM adapter without changing its
  request shape, retries, parsing, exceptions, or structured-response correction loop.
- [x] 4.2 Add the Bedrock Converse adapter with lazy injected client construction, system/conversation and
  inference mapping, text response parsing, and provider error classification into existing runtime errors.
- [x] 4.3 Add centralized adapter preflight, including Bedrock Converse capability checks that report the
  resolved SDK version and import path before any LLM-dependent check runs.
- [x] 4.4 Add and justify a pinned CI-only AWS SDK dependency in the single requirements file, keeping it out
  of child-vendored tooling and LiteLLM/local execution paths.
- [x] 4.5 Expand runtime tests with injected LiteLLM HTTP and Bedrock clients for provider selection,
  request/response mapping, retries, errors, preflight, structured correction, and lazy dependency loading.

## 5. Independent provider PR workflows

- [x] 5.1 Create `panopticon-pr-litellm.yml` with canonical workflow-call inputs/secrets and the complete
  existing PR evaluation contract, without AWS permissions or dependency setup.
- [x] 5.2 Create `panopticon-pr-bedrock.yml` with canonical workflow-call inputs/secrets, both trusted
  Bedrock credential modes, isolated `actions/setup-python` dependency installation, preflight, and the
  complete existing PR evaluation contract.
- [x] 5.3 Convert the instance-side generic `panopticon-pr.yml` into a legacy guard that checks out the child,
  resolves its recorded instance, and fails with complete instance-configuration and child-bootstrap
  remediation instead of a workflow-load error.
- [x] 5.4 Add early provider-workflow validation for empty canonical secrets/inputs, credential-mode
  requirements, mismatched config revisions, and actionable summaries for explicit credential-action and
  branch-state failures before or after provider work as applicable.
- [x] 5.5 Add workflow parity and contract tests that validate required inputs, secrets, permissions, common
  PR phases, timeout mapping, independent-check behavior, reporting, gating, both credential modes, and
  actionable failure summaries.

## 6. Recovery and migration behavior

- [x] 6.1 Centralize user-facing unconfigured/stale credential-mode remediation in a shared formatter,
  vendored after successful bootstrap; retain self-contained fallbacks before vendoring and in the legacy
  caller guard, without exposing credential values.
- [x] 6.2 Ensure unconfigured failures print the resolved `Configure Panopticon` Actions URL, ordered console
  steps, equivalent `gh workflow run`/run-watch commands, and the resolved default branch.
- [x] 6.3 Ensure stale and renamed-secret failures print the exact one-line command
  `curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='<owner/repo>' python3`
  plus child-root, review, commit, push, and workflow-rerun instructions.
- [x] 6.4 Add exact-output tests for missing provider, legacy caller, changed provider, changed name,
  credential-mode/action failure, revision mismatch, empty old instance-token mapping, private instance,
  and custom workflow-ref recovery paths.
- [x] 6.6 Rename the template-owned reusable sync workflow to the explicit
  `shared-template-sync-caller-only.yml`; update the fixed instance caller, documentation, and tests while
  retaining token fallback, protected-path merge behavior, and recovery in the shared workflow.
- [x] 6.5 Implement and test the staged compatibility rollout so configuration support lands before strict
  enforcement and old provider workflows/secrets remain usable until child callers are regenerated.

## 7. Architecture and documentation hygiene

- [x] 7.1 Update the Panopticon architecture and Python-tooling skills to permit only justified, pinned,
  CI-only SDKs inside built-in provider adapters while preserving the stdlib-only child/local contract.
- [x] 7.2 Reconcile the active `docs/explore/workflow-customization.md` record with the accepted
  instance-configured, separate-workflow design. The historical action-plan files
  `llm-provider-plugins.md`, `ci-dependency-isolation.md`, `oidc-caller-permissions.md`,
  `runtime-preflight.md`, and `configurable-instance-token.md` are not present in this repository.
- [x] 7.3 Update `docs/setup-guide.md`, `docs/testing.md`, `docs/planned-work.md`, and `CHANGELOG.md` with both
  provider setup paths, trusted Bedrock credential-mode choices, clear field labels and examples, exact
  console/CLI/bootstrap recovery, safe secret-name rotation, migration ordering, test coverage, and the
  template-sync protection boundary: protected paths/config/generated diagram survive, unprotected
  template-managed customizations can update or conflict, and child tooling sync is not protected.
- [x] 7.5 Run the full unit suite, strict OpenSpec validation, workflow validation, and markdown lint after
  credential-mode implementation; fix all in-scope failures and verify no archived OpenSpec history changed.
- [x] 7.4 Run the full unit suite, strict OpenSpec validation, workflow validation, and markdown lint; fix all
  in-scope failures and verify no archived OpenSpec history was rewritten.
- [x] Restructure `README.md` as concise orientation and navigation: retain the project logo and prominent
  organization-architecture link at the top, plus purpose, roles, and the primary
  lifecycle; link detailed setup and reference documentation; remove detailed procedures, implementation
  inventories, and transient implementation-status sections such as dependency-indexing CI wiring status;
  add the specified YouTube thumbnail that opens its watch page in a new browser tab or window at the end. (`docs/spec.md` is not present
  in this repository)
