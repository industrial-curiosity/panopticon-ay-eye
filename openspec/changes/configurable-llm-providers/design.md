# Configurable LLM providers design

## Context

Panopticon's CI LLM client currently assumes one OpenAI-compatible transport, fixed Actions names, and an
implicit LiteLLM-compatible deployment. A production instance proved that native Bedrock through GitHub
OIDC requires a provider SDK, different authentication and message mapping, additional caller permissions,
and isolated Python setup. The existing child installer already fetches instance configuration and generates
thin reusable-workflow callers, but it silently converts every org-config fetch failure to an empty object
and assumes local and remote workflow filenames match.

This design makes provider selection an explicit instance-bootstrap operation. The template remains
unconfigured, while a manual workflow persists a validated provider contract. Child bootstrap compiles that
contract into a stable local PR caller pointing to one independent provider workflow in the instance.

## Goals / Non-Goals

**Goals:**

- Make LiteLLM and native Bedrock/OIDC work without instance forks.
- Require an explicit provider choice and retain organization-specific secret and variable naming.
- Keep child workflows thin, generated, and free of provider implementations.
- Preserve the shared LLM client behavior and complete PR evaluation semantics across provider workflows.
- Fail before mutation on invalid instance configuration and fail stale callers with copy/paste recovery.
- Keep Bedrock's SDK and setup isolated from LiteLLM jobs, child tooling, and local agent flows.

**Non-Goals:**

- Runtime-installable third-party provider plugins.
- Per-child provider selection; one instance contract applies organization-wide.
- Automatic creation or mutation of org secrets, variables, AWS roles, or OIDC trust policies.
- Copying full provider workflows into child repositories.
- Abstracting provider workflows into a generic workflow-hook or arbitrary workflow-path mechanism.
- Replacing local agent-harness execution with Panopticon CI credentials.

## Decisions

### D1: Instance config is authoritative and initially unconfigured

The template omits the `llm` provider block. `load_org_config` continues to load unrelated defaults so
template sync and configuration can operate, while a separate strict provider resolver rejects missing or
invalid provider state wherever it is required. This avoids making general config parsing unusable before
bootstrap while ensuring no provider silently wins.

Alternative considered: default to LiteLLM for compatibility. Rejected because it recreates the accidental
configuration this change is intended to eliminate.

### D2: A manual workflow writes names, not values

`.github/workflows/configure-panopticon.yml` exposes a sentinel provider choice plus name inputs with
provider-specific defaults. An importable standard-library module validates and normalizes the document;
the workflow checks out the instance, invokes that module, commits only `panopticon.config.json`, and writes
the next setup steps to its summary. Secret values remain solely in GitHub Actions secrets and never appear
in dispatch inputs, logs, commits, or outputs.

The provider registry owns workflow paths, logical fields, defaults, permissions, and dependency metadata.
Configuration stores the selected provider and name overrides, not an executable workflow path.

### D3: Provider workflows are independent reusable entrypoints

The instance contains `panopticon-pr-litellm.yml` and `panopticon-pr-bedrock.yml`. Each declares canonical
inputs and secrets and owns the full PR evaluation job, including its provider setup and permissions. The
stable child-local `panopticon-pr.yml` points to exactly one of them. Merge and PR-close remain
provider-independent.

This accepts some YAML duplication. Provider-independent Python behavior remains shared, while tests assert
that both entrypoints preserve the required PR phases, exit-code handling, reporting, and gating. A generic
nested workflow was rejected because a portable template cannot dynamically self-reference the future
private instance slug/ref in `jobs.<id>.uses`, and credentials or step state cannot be passed from a provider
setup job into a different reusable-workflow job.

### D4: Generated callers map configured names explicitly

Bootstrap evolves from a tuple of matching filenames to logical caller definitions. For the PR role it
selects the remote provider filename, emits that workflow's exact permission set, passes variable values as
canonical `with` inputs, and maps configured org secret names to canonical `workflow_call.secrets` names.
It does not use `secrets: inherit`. Provider-independent merge and close callers use the configured instance
token name but retain their existing remote targets.

The installer fetches and validates the provider contract and verifies the selected provider workflow exists
at the effective `workflow_ref` before prompting or writing. `fetch_org_config` stops swallowing errors.

### D5: Caller-relevant configuration is revisioned

A canonical JSON serialization of effective provider identifier, workflow, permissions, logical names, and
contract version is hashed. Bootstrap embeds the revision as a required workflow input. After child checkout
and before provider work, the reusable workflow reads live instance config and compares revisions. A mismatch
is an operational failure requiring bootstrap regeneration.

An empty renamed instance-token mapping can prevent instance checkout, so validation of the canonical token
input happens first and uses the child repo's recorded instance identity for remediation. Safe secret-name
rotation therefore keeps the old secret available until callers are regenerated; failure remains explicit if
that order is not followed.

### D6: Recovery text is a tested interface

Unconfigured-provider output contains:

1. The resolved direct Actions URL for `configure-panopticon.yml`.
2. Ordered UI steps naming **Run workflow**, the branch selector, provider choice, name fields, and success
   condition.
3. An equivalent `gh workflow run` command and a command to observe completion.
4. The exact child bootstrap one-liner:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='acme/panopticon-instance' python3
   ```

Stale-caller output uses the same one-liner and explicitly instructs the user to run it inside the child
clone, review generated changes, commit, push, and rerun or await CI. The instance slug and branch are
substituted dynamically. Detailed recovery lives in the step summary; `::error::` remains one concise line.
Tests assert commands and URLs, not vague keywords.

### D7: LiteLLM transport is extracted; Bedrock is a lazy CI-only adapter

The current HTTP behavior moves behind a LiteLLM adapter without request or response changes. The Bedrock
adapter maps system and conversation turns to Converse, maps inference configuration and response text, and
classifies provider errors into existing runtime exceptions. The shared structured-response correction loop
stays above both.

Bedrock lazily imports a pinned AWS SDK. Only its workflow runs `actions/setup-python` and a single
`pip install --upgrade -r requirements.txt` setup before preflight. The dependency is never included in
`LOCAL_TOOLING_MODULES`. This deliberately narrows the architecture rule prohibiting provider SDKs: the core
and child contract remain standard-library-first, while a built-in CI adapter may justify one pinned SDK.

### D8: Provider preflight is centralized

Each adapter implements a preflight. Bedrock constructs the runtime client and verifies Converse support,
reporting resolved SDK version and import path on failure. LiteLLM validates its mapped configuration; it
does not make an extra billable inference request. Preflight runs once before the independent LLM checks.

## Risks / Trade-offs

- [Separate provider workflows can drift] → Add parity tests for common PR phases and keep substantive
  provider-independent logic in Python modules.
- [Configuration workflow cannot verify org secret values] → Validate names, print exact setup requirements,
  and retain bootstrap's report-only org API check when suitable auth exists.
- [Default-branch protection can reject the configuration commit] → Fail with the exact generated diff and
  local/PR recovery instructions; never claim configuration succeeded without a committed file.
- [Provider or name changes leave existing child callers stale] → Compare deterministic revisions and retain
  the legacy guard and old provider entrypoints as loud migration surfaces.
- [Removing an old instance-token secret blocks live-config checkout] → Validate the canonical token before
  checkout and print the child installer command from recorded child config.
- [Bedrock models differ in Converse support] → Require an explicit model identifier and fail during provider
  preflight or the first classified provider request with model-specific guidance.
- [A third-party SDK weakens checkout-and-run simplicity] → Pin it, install it only in the Bedrock workflow
  under `actions/setup-python`, and verify its resolved capability and import path.

## Migration Plan

1. Ship the configuration workflow, provider schema/registry, independent provider workflows, and legacy
   guard before enforcing provider selection for existing callers.
2. Have instance maintainers sync the preparatory release and run `Configure Panopticon`; existing LiteLLM
   users explicitly select LiteLLM and may retain current Actions names.
3. Enable strict provider enforcement and provider-aware child caller generation.
4. Rerun the bootstrap installer in each child, commit and push generated caller updates, and keep any renamed
   old instance-token secret available until this completes.
5. Confirm provider workflows pass preflight and PR evaluation before removing obsolete secret names or
   retiring compatibility workflow versions.

Rollback retains the committed provider config and restores prior caller targets/workflow ref. Do not remove
legacy/provider workflows or old secret names until every child is confirmed regenerated; doing so would
turn an actionable runtime guard into a workflow-load or empty-secret failure.

## Open Questions

None. Provider scope, separate workflow entrypoints, instance-owned configuration, explicit name mapping,
and recovery-command behavior were resolved during exploration.
