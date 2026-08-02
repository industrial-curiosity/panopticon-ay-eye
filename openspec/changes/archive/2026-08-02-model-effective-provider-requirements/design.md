# Effective Provider Requirements Design

## Context

The provider registry currently maps logical names to organization Actions names
but does not say which values are optional or where an absent value can be
resolved. Bootstrap and finalization therefore report every missing name as a
missing prerequisite, even when a trusted workflow has a safe default or an
instance supplies a value. The resulting guidance makes organization setup
harder than necessary and obscures the actual remediation path.

## Goals / Non-Goals

**Goals:**

- Model required versus optional logical provider values in the trusted contract.
- Resolve optional non-secret values deterministically in this order: explicit
  organization Actions value, fixed instance-action output, instance-configured
  non-secret default, then template workflow default.
- Keep authentication, repository access, and provider credentials required.
- Give integrators one concise source-of-truth table and command path for every
  provider value, including a clear explanation when no effective value exists.
- Preserve the closed provider registry and fixed reviewed action paths.

**Non-Goals:**

- Accepting, persisting, or printing credential values.
- Allowing an organization configuration to select arbitrary workflows or
  Actions.
- Inferring an effective value from a missing or blank source.
- Changing provider-specific transport behavior or default values unrelated to
  requirement resolution.

## Decisions

### Contract-owned requirement metadata

The trusted provider registry will declare which variable logical names are
optional and which template defaults are available. Optional names must be a
validated subset of the selected provider and credential mode's registered
variables. Secrets, the instance token, provider API keys, and authentication
values remain required and cannot be defaulted through this feature.

The persisted `llm` block will accept a validated `defaults` map for non-secret
optional logical names. Its values are literal non-empty strings and become part
of the effective provider contract and its revision. This lets an instance
record a stable organization default without putting it in every child repo.
For `job_timeout_minutes`, which GitHub evaluates before any job step, the
generated child caller embeds the validated instance default. Its supported
order is therefore organization Actions value, instance configuration default,
then template workflow default; the instance action cannot participate.

### Fixed instance default resolver

An instance may provide optional values dynamically only through the fixed,
reviewed path `.github/actions/panopticon-provider-defaults/action.yml`. The
action has a closed, declared output interface keyed by optional logical names;
it cannot select another action, workflow, or credential source. It receives no
credential values and its outputs must be non-empty, non-secret strings.

The reusable provider workflow checks out the instance and invokes this action
before provider preflight. A missing action or an invalid output is a clear
configuration error only when that output is needed to resolve an otherwise
absent optional value. This retains a simple path for organizations that only
use Actions variables or static config defaults.

### One resolver and visible provenance

Provider workflows will pass raw caller inputs to a deterministic resolver
instead of applying GitHub-expression defaults before source selection. The
resolver returns each effective value plus a source label: `organization
variable`, `instance action`, `instance config`, or `workflow default`.
It never prints a value. Bootstrap and finalization use the same contract
metadata to classify names as required, supplied by a default, or unresolved.

The choice favors a single deterministic Python implementation over duplicated
shell/YAML precedence logic. It also prevents a workflow default from masking a
higher-priority empty source before the fixed action can run.

Job timeout is resolved in the generated caller rather than this runtime
resolver. GitHub evaluates `timeout-minutes` before checkout, so action output
is unavailable at that boundary. Embedding the reviewed non-secret instance
default preserves a visible, deterministic value and causes caller regeneration
when it changes.

### Integrator-first guidance

The setup guide and workflow summaries will use the same generated contract
view: logical purpose, whether the value is required, allowed sources in
precedence order, the configured Actions name when applicable, and the exact
next action. Instructions will begin with the simplest supported path (an
organization variable), then describe when to use an instance default or fixed
action. Errors will name the logical value and source(s) checked, never a
secret value.

## Risks / Trade-offs

- [A dynamic action can add organization complexity] → keep its path and
  outputs fixed, optional, documented, and unnecessary for static defaults.
- [A default can accidentally mask configuration drift] → include optionality,
  default declarations, and fixed-action use in the contract revision and fail
  when no source produces a required effective value.
- [Different surfaces can disagree about status] → use common resolver metadata
  and test bootstrap, finalization, caller generation, and workflows together.
- [Clear reports could expose sensitive information] → report only logical
  names and source labels; reject default values that look like credentials.

## Migration Plan

1. Extend the registry and instance-config validator while retaining existing
   configurations as valid required-name contracts.
2. Add the fixed default-resolver action, reusable resolver, and workflow
   wiring without changing existing organization variables; embed any validated
   instance job-timeout default in regenerated callers.
3. Regenerate child callers when the new contract revision is detected.
4. Publish an ordered setup guide: configure required values first, then choose
   an optional-value source only when needed, run the validation command, and
   rerun bootstrap for stale callers.
5. Roll back by removing optional/default declarations from the instance config;
   explicit organization Actions values continue to work unchanged.

## Open Questions

None. The chosen precedence is organization Actions value, fixed instance-action
output, instance configuration default, then template workflow default.
