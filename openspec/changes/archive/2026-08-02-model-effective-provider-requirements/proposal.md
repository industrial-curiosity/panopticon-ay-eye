# Model Effective Provider Requirements

## Why

Provider setup currently treats every configured logical name as required even
when a trusted workflow, instance configuration, or fixed instance action
supplies an effective value. This creates false prerequisite failures and gives
organization integrators no single, deterministic explanation of where a value
must be configured.

## What Changes

- Add required/optional semantics to the trusted provider contract and include
  them in its deterministic revision.
- Resolve each logical provider value using a documented precedence order:
  organization Actions value, fixed instance-action output, non-secret instance
  configuration default, then template workflow default; generated callers carry
  the instance default for job timeout because GitHub resolves job timeout before
  an action can run.
- Fail before provider work when an optional value has no effective value, while
  preserving repository access and authentication as mandatory requirements.
- Update bootstrap, finalization, caller generation, workflow summaries, and
  integration documentation to present required values, optional values,
  effective sources, and exact recovery commands clearly.
- Add deterministic validation and regression coverage for both default sources,
  empty organization collections, invalid optional names, and absent defaults.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `llm-provider-configuration`: define trusted optionality, default-source
  precedence, fixed instance-action outputs, and integrator-facing setup and
  recovery guidance.
- `repo-initialization`: require bootstrap and finalization to distinguish
  required configuration from values supplied by trusted defaults.
- `pr-evaluation`: require provider workflows to resolve and report effective
  provider values before provider preflight and LLM work.

## Impact

Affected surfaces include provider-contract validation, instance configuration,
fixed local Actions, generated child callers, bootstrap and finalization
reports, reusable provider workflows, tests, setup documentation, and the
relevant OpenSpec requirements. No credential value is accepted, written, or
reported by this change.
