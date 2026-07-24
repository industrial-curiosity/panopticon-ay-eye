# Split provider configuration workflows design

## Context

The current `.github/workflows/configure-panopticon.yml` is a single manual
workflow that asks the
maintainer to replace a provider sentinel and displays the union of LiteLLM and
Bedrock inputs. GitHub
Actions dispatch forms are static, so fields labelled as ignored remain visible
after the provider choice.
The workflow also contains the complete validation, persistence, summary, and
Git commit/push implementation.

The underlying Python boundary is already appropriate:
`panopticon.configure_instance.configure` accepts a
closed provider identifier plus logical Actions names, resolves the trusted
registry, and writes only the
`llm` block. The split should improve the user-facing workflow surface without
creating separate
configuration schemas or provider-specific Python implementations.

## Goals / Non-Goals

## Goals

- Give LiteLLM and Bedrock separate, clearly named manual configuration
  entrypoints.
- Show only provider-relevant names and examples in each dispatch form.
- Keep validation, persistence, no-op detection, commit/push behavior, and
  failure summaries identical.
- Preserve the trusted registry, persisted configuration schema, contract
  revision, and child caller format.
- Give unconfigured maintainers complete console and CLI recovery paths for
  either provider.
- Prevent the two workflows from writing instance configuration concurrently.

## Non-Goals

- Splitting Bedrock again by credential mode.
- Making provider workflows, credential actions, or configuration fields
  extensible through arbitrary paths.
- Creating or validating organization secret values, AWS roles, or endpoint
  availability.
- Changing provider-specific PR evaluation workflows or requiring child
  bootstrap regeneration when the
  effective provider contract is unchanged.
- Retaining the generic provider-selection workflow as a third runnable
  entrypoint.

## Decisions

### D1: Two fixed manual entrypoints replace the generic selector

The template will provide `.github/workflows/configure-panopticon-litellm.yml`
and
`.github/workflows/configure-panopticon-bedrock.yml`, displayed as **Configure
Panopticon — LiteLLM** and
**Configure Panopticon — Bedrock**. Each uses `workflow_dispatch` and passes its
provider as a literal rather
than accepting a provider input.

The LiteLLM form exposes the instance-token secret name, API-key secret name,
endpoint variable name, model
variable name, and common request/job-budget variable names. The Bedrock form
exposes the instance-token
secret name, credential mode, model variable name, conditional AWS region and
role-ARN names, and the common
budget names. Bedrock keeps one credential-mode choice because both modes belong
to the same trusted provider
contract; splitting modes would multiply entrypoints without removing the
remaining need to explain their
relationship.

Alternative considered: retain one selector and improve descriptions. Rejected
because static dispatch
forms would continue showing irrelevant provider inputs.

### D2: A local composite action owns shared mutation behavior

Both workflows will check out the instance and invoke
`.github/actions/configure-panopticon/action.yml`. The action receives an
explicit provider plus logical name
inputs, exposes the checked-out workspace on `PYTHONPATH`, calls the existing
configuration module, writes
success or failure details to `GITHUB_STEP_SUMMARY`, detects a no-op, and
commits and pushes only
`panopticon.config.json`.

A composite action keeps exactly two runnable workflows in the Actions interface
while avoiding duplicated
shell and inline Python behavior. It is preferred over a third reusable workflow
because the requested
surface is one runnable workflow per provider, and preferred over copying steps
because summary and push
recovery behavior must not drift.

The action's provider input is still validated by the closed registry.
User-facing workflows pass only
literal trusted values; neither workflow accepts an arbitrary action path or
provider workflow path.

### D3: Provider-neutral Python and persisted contracts remain stable

`panopticon.configure_instance` remains the single deterministic configuration
engine. The workflow-only
`select-a-provider` sentinel is removed from dispatch forms and recovery text;
the Python API continues to
reject any identifier outside the trusted registry.

The `panopticon.config.json` shape, provider defaults, workflow registry, and
revision serialization remain
unchanged. Re-running the matching new workflow with the same names therefore
produces a byte-for-byte no-op,
and existing child callers do not become stale solely because configuration
entrypoints moved.

### D4: Unconfigured recovery presents both provider paths

An unconfigured instance has no basis for choosing a provider on the
maintainer's behalf. Recovery output
will therefore present:

1. The direct LiteLLM workflow URL and equivalent `gh workflow run` command.
2. The direct Bedrock workflow URL and equivalent `gh workflow run` command.
3. Shared instructions to choose the instance branch, enter names rather than
   values, wait for the committed
   configuration, and rerun child bootstrap with the existing exact installer
   command.

Legacy caller guards, bootstrap errors, setup documentation, and exact-output
tests will use the same two
filenames. Provider-specific stale-caller recovery remains focused on rerunning
child bootstrap when the
instance is already configured.

### D5: Both entrypoints share a configuration concurrency group

Both workflows will use the same repository-scoped concurrency group with
in-progress cancellation disabled.
This prevents simultaneous checkouts from racing to commit different provider
configurations. A later queued
dispatch may intentionally replace the earlier provider after it completes;
ordinary Git history and the
existing no-op/push-failure summary remain the audit and recovery surfaces.

Alternative considered: rely only on push rejection. Rejected because a known
cross-workflow mutation race
can be prevented before either workflow constructs a stale diff.

## Risks / Trade-offs

- [The composite action introduces a new repository-local action pattern] → Keep
  it narrowly scoped to the
  existing deterministic configure-and-commit steps and cover every
  caller/action contract structurally.
- [A maintainer may dispatch both provider workflows without understanding that
  the latter changes the
  organization-wide provider] → Use explicit workflow names, serialize runs, and
  state in both descriptions
  and summaries that configuration is instance-wide.
- [Removing the generic filename breaks saved links and commands] → Template
  sync adds both new workflows in
  the same update that replaces all generated recovery text and documentation;
  dual-path recovery names both
  replacements.
- [Bedrock still exposes AWS name fields when `instance-managed` is chosen] →
  Clearly label them as
  GitHub-OIDC-only; credential modes remain one provider contract and do not
  justify more workflows.
- [Shared action failures could become less visible behind a caller step] →
  Preserve concise annotations and
  write the detected cause plus correction directly to the workflow step summary
  before every explicit
  non-zero exit.

## Migration Plan

1. Add the shared composite action and both provider-specific dispatch
   workflows.
2. Update recovery code, the legacy PR guard, tests, documentation, and
   architecture guidance to reference
   both new filenames.
3. Remove the generic `configure-panopticon.yml` only in the same template
   change so no committed code points
   to the removed path.
4. Existing instances run template sync to receive the two entrypoints and
   removal of the generic one.
   Already configured instances require no configuration or child caller change
   unless the maintainer wants
   to change provider names or credential mode.
5. New or unconfigured instances run exactly one provider-specific workflow,
   then continue child bootstrap.

Rollback restores the generic workflow and its recovery references. The
persisted provider block needs no
migration in either direction.

## Open Questions

None.
