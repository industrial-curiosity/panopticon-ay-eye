# Split provider configuration workflows

## Why

The current `Configure Panopticon` workflow presents one mixed form containing
both LiteLLM and Bedrock
fields, forcing maintainers to select a provider and interpret inputs that do
not apply to their choice.
Separate provider-specific entrypoints will make configuration explicit, reduce
invalid or confusing input,
and preserve the same trusted provider contract.

## What Changes

- Replace the generic `configure-panopticon.yml` dispatch workflow with
  independently runnable LiteLLM and
  Bedrock configuration workflows whose provider identity is fixed.
- Show only the secret and variable name inputs relevant to the selected
  provider, while retaining common
  instance-token and request/job-budget name inputs.
- Centralize the shared validation, persistence, commit/push, no-op, and
  actionable failure-summary steps in
  one checked-in composite action used by both workflows.
- Replace the generic provider-selection recovery path with both direct workflow
  URLs and both equivalent
  `gh workflow run` commands.
- Serialize both configuration entrypoints through one concurrency group so
  concurrent dispatches cannot
  update `panopticon.config.json` simultaneously.
- Remove the workflow-only `select-a-provider` sentinel while retaining the
  closed trusted provider registry
  and provider-neutral Python configuration engine.
- Update tests, setup guidance, architecture guidance, and exact recovery-output
  contracts for the two
  provider-specific entrypoints.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `llm-provider-configuration`: Replace the single provider-selecting dispatch
  workflow with fixed LiteLLM
  and Bedrock entrypoints, provider-relevant input forms, shared execution
  behavior, and dual-path recovery.
- `pr-evaluation`: Update legacy and unconfigured-provider recovery requirements
  to direct maintainers to
  both provider-specific configuration workflows instead of one generic
  selector.

## Impact

The change affects GitHub Actions configuration workflows, their shared local
action, recovery formatting,
bootstrap and legacy-guard messages, workflow structural tests, exact-output
recovery tests, the setup and
testing documentation, and the Panopticon architecture skill. The persisted
`panopticon.config.json` schema,
provider contract revision algorithm, provider-specific PR workflows, and
generated child caller format do
not change, so an existing configured instance does not require child
regeneration solely because of this
workflow split.
