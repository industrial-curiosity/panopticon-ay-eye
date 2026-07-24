# Split provider configuration workflows tasks

## 1. Shared configuration execution

- [x] 1.1 Add `.github/actions/configure-panopticon/action.yml` with explicit
  logical-name inputs and the
  existing provider validation, checked-out `PYTHONPATH`, deterministic
  persistence, success/failure
  summaries, no-op detection, and commit/push recovery behavior.
- [x] 1.2 Keep `panopticon.configure_instance` provider-neutral and
  closed-registry validated while removing
  the workflow-only `select-a-provider` sentinel from its CLI surface and tests.

## 2. Provider-specific workflow entrypoints

- [x] 2.1 Add `configure-panopticon-litellm.yml` with fixed LiteLLM identity,
  only LiteLLM/common name inputs,
  `contents: write`, instance checkout, the shared local action, and the common
  configuration concurrency
  group.
- [x] 2.2 Add `configure-panopticon-bedrock.yml` with fixed Bedrock identity,
  credential-mode and
  Bedrock/common name inputs, provider-specific examples, `contents: write`,
  instance checkout, the shared
  local action, and the same concurrency group.
- [x] 2.3 Remove the generic `configure-panopticon.yml` only after both new
  callers and every in-repository
  reference to its selector and filename have replacements.

## 3. Recovery and migration behavior

- [x] 3.1 Update `panopticon.recovery.configuration_recovery` and bootstrap
  output to show both direct
  provider workflow URLs, both branch-specific `gh workflow run` commands,
  ordered provider-choice
  instructions, and the unchanged exact child-bootstrap command.
- [x] 3.2 Update the legacy PR guard and provider-related messages so
  unconfigured instances use the dual
  configuration paths while stale configured callers continue to receive only
  the exact regeneration
  instructions they need.
- [x] 3.3 Verify with tests that unchanged persisted provider configuration
  produces the same effective
  contract revision and does not require child caller regeneration after the
  workflow split.

## 4. Automated coverage and validation

- [x] 4.1 Replace generic configuration-workflow assertions with structural
  tests proving both callers use
  fixed providers, expose no cross-provider inputs, grant only required
  permissions, share one local action,
  and use one concurrency group.
- [x] 4.2 Expand configuration-action tests to cover LiteLLM and both Bedrock
  credential modes, invalid names,
  no-op reruns, push-failure summaries, clean-runner imports, and exclusion of
  credential values.
- [x] 4.3 Update exact recovery and installer tests for both workflow URLs and
  CLI commands, removal of the
  sentinel, private instance slugs, non-default branches, and the legacy
  self-contained fallback.
- [x] 4.4 Run the complete Python unit suite, workflow structural validation,
  strict OpenSpec validation, and
  Markdown lint; fix every failure introduced by this change.

## 5. Documentation

- [x] 5.1 Update `docs/setup-guide.md`, `docs/testing.md`,
  `docs/explore/workflow-customization.md`, the Panopticon architecture skill,
  and `CHANGELOG.md` with the
  two provider entrypoints, shared behavior, migration sequence, and unchanged
  child caller contract.
- [x] Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes introduced by this change
