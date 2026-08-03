# Design: Harden bootstrap manifest and workflow CI

## Context

The selected instance ref is the authority for child-safe tooling. Local sync
already retrieves a Python manifest from that ref, but bootstrap imports a
local manifest instead. The default installer loader does not register that
module before importing bootstrap, which makes an uncustomized instance
bootstrap fail. The Python manifest is also executed by sync merely to read a
file list.

Workflow-contract validation currently accepts individual paths and tests only
the three provider PR workflows. No repository-owned GitHub Actions workflow
runs either that validator or the full unit suite.

## Goals / Non-Goals

**Goals:**

- Establish one versioned, data-only manifest authority at the selected
  instance ref.
- Make bootstrap and sync validate and stage the complete managed module set
  before writing it.
- Keep unknown child files untouched and their warnings advisory.
- Validate every shipped reusable workflow in a no-secret CI run.
- Retain standard-library-only Python tooling and explicit trust boundaries.

**Non-Goals:**

- Deleting legacy or CI-only files from child repositories.
- Changing provider contracts, child caller generation, or provider runtime
  behavior.
- Validating arbitrary YAML or GitHub expressions beyond the existing
  dot-form `inputs.<name>` and `secrets.<name>` contract check.
- Adding third-party parsers or a new package manager dependency.

## Decisions

### Use a versioned JSON manifest at a fixed path

Replace `panopticon/local_tooling.py` as the manifest with
`panopticon/local-tooling.json` containing exactly a positive integer
`schema_version` and a non-empty `modules` array of unique, flat `.py`
filenames. Bootstrap, sync, and tooling-currency reject malformed documents,
unknown schema versions, duplicate names, path separators, traversal names, or
module paths absent from the selected instance tree.

JSON keeps data interpretation deterministic and avoids executing instance
content merely to determine a file list. A Python manifest was rejected because
sync currently uses `exec()` to read it. A manifest embedded in bootstrap was
rejected because it becomes stale when an instance changes its approved local
tooling set.

### Bootstrap fetches and stages the selected manifest itself

Bootstrap will retrieve the JSON manifest with its existing authenticated
GitHub-contents client at the requested instance ref, fetch every listed module
into memory, then write the complete set. It will not import a manifest module.
This removes the missing-import dependency from the default payload loader and
ensures direct bootstrap execution uses the same authority as sync.

Sync follows the same parse-and-stage sequence. Tooling-currency reads the
manifest from the already checked-out instance repository; it does not read a
child copy or execute a manifest. All paths outside the selected manifest stay
unmanaged, are classified as instance-excluded or child-only where applicable,
and are never deleted.

### Discover reusable workflows deterministically

Add a standard-library discovery function to `panopticon.workflow_contracts`
that returns the repository workflow files declaring a root-level
`on.workflow_call`. The command-line interface will accept a workflow directory
and validate the discovered paths in deterministic order. Existing explicit
path arguments remain supported for focused diagnostics.

Discovery avoids an error-prone fixed list as new reusable workflows are
added. It deliberately remains a narrow source scanner, consistent with the
existing validator, rather than introducing a YAML dependency.

### Add a no-secret template-validation workflow

Add a root GitHub Actions workflow for pull requests, pushes, and manual
dispatch. It uses read-only permissions, checks out the repository, validates
all reusable workflow contracts, and runs the full standard-library Python
suite. It receives no provider, instance, or organization credentials.

The existing provider workflows remain child-facing evaluation workflows; this
new workflow verifies the public template itself.

## Risks / Trade-offs

- [Instances on older refs lack the JSON manifest] → Bootstrap and sync fail
  before writing tooling with an exact upgrade/retry message; rollout ships the
  manifest and consumers in one template change.
- [Bootstrap and sync duplicate a small manifest parser] → Keep the schema
  deliberately small and use the same fixture tests for both consumers. A
  shared import would recreate the default-loader dependency that this change
  removes.
- [A new reusable workflow is missed by discovery] → Test discovery against all
  checked-in reusable workflows and run it in repository CI on every template
  change.
- [Template CI becomes a release dependency] → The workflow is credential-free
  and uses only Python's standard library, so it neither calls a provider nor
  depends on private instance access.

## Migration Plan

1. Land the JSON manifest, consumers, tests, and template CI together.
2. Existing child repositories use local sync to acquire the refreshed sync
   module and manifest-listed tooling; sync preserves the legacy Python
   manifest as an unmanaged, reviewable file until maintainers remove it
   separately.
3. Instance repositories consume the new behavior only after syncing the
   complete change. Before that, the selected old ref continues using its
   current bootstrap and sync contract.
4. If a release must be rolled back, point child callers and installer use back
   to the last known-good instance ref; no child data has been deleted.

## Open Questions

None. The manifest schema, fixed path, CI scope, and backward-compatible
unmanaged-file treatment are resolved by this change.
