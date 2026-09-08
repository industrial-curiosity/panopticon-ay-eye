# Tooling Currency Spec

## Purpose

Define how initialized child repositories detect and refresh managed Panopticon
skills, vendored tooling, and their workflow alignment with the configured
instance repository.

## Requirements

### Requirement: Workflow-ref alignment check

The PR workflow SHALL determine whether a child repo's wired `panopticon-pr.yml`
caller workflow
(`uses: <instance>/.github/workflows/panopticon-pr.yml@<ref>`) currently
resolves to the same
commit as the instance repo's default branch tip, using the instance repo
checkout the PR workflow
already performs — no tag enumeration, no additional checkout configuration.
Equal → no warning.
Different, or the ref does not resolve to any commit on the instance repo → the
check SHALL emit a
non-blocking `::warning::` naming the wired ref and that it no longer matches
the instance's
current default branch.

#### Scenario: Wired ref matches the instance's current default branch tip

- **WHEN** a child repo's caller workflow is wired to a ref that resolves to the
  same commit as the
  instance repo's current default branch tip
- **THEN** the check emits no warning

#### Scenario: Wired ref resolves to an older commit

- **GIVEN** a child repo's caller workflow is wired to a tag or branch that
  resolves to a commit
  behind the instance repo's current default branch tip
- **WHEN** the workflow-ref alignment check runs
- **THEN** it emits a non-blocking `::warning::` naming the wired ref, left to
  the child repo
  maintainer's discretion to act on or ignore

#### Scenario: Wired ref no longer exists

- **GIVEN** a child repo's caller workflow is wired to a tag that has since been
  deleted from the
  instance repo
- **WHEN** the workflow-ref alignment check runs
- **THEN** it emits a non-blocking `::warning::` stating the wired ref could not
  be resolved

### Requirement: Skills and tooling drift check

The PR workflow SHALL compare, by content, the child repo's downloaded
`panopticon-*` skills and
vendored local-tooling modules against the instance repo's current copies of the
same files, using
the instance repo checkout the PR workflow already performs. Comparison SHALL be
content-based
(e.g. a direct diff, or a hash comparison) — file modification timestamps SHALL
NOT be used as a
staleness signal, since CI checkout timestamps reflect checkout time, not commit
history, and would
produce false or missed findings. Any file that differs, is missing from the
child, or is missing
from the instance's current copy SHALL be named in a non-blocking `::warning::`.

The child repo's skills location (which of the candidate locations documented in
`docs/agentskills-support.md` the repo's skills live in) SHALL be determined the
same way the
bootstrap installer's idempotent re-run already determines it, not by requiring
a new persisted
configuration field.

#### Scenario: Skills content matches the instance

- **WHEN** every `panopticon-*` skill file in the child repo has identical
  content to the instance
  repo's current copy
- **THEN** the check emits no warning for skills

#### Scenario: A vendored tooling module has drifted

- **GIVEN** the child repo's vendored `panopticon/docs.py` differs in content
  from the instance
  repo's current `panopticon/docs.py`
- **WHEN** the skills and tooling drift check runs
- **THEN** it emits a non-blocking `::warning::` naming `panopticon/docs.py` as
  out of date

#### Scenario: A skill exists in the instance but not the child

- **GIVEN** the instance repo has a `panopticon-*` skill the child repo has
  never downloaded
- **WHEN** the skills and tooling drift check runs
- **THEN** it emits a non-blocking `::warning::` naming the missing skill

### Requirement: Tooling-currency checks are always advisory

The workflow-ref alignment and skills/tooling drift checks SHALL remain
advisory. Neither check SHALL have an entry in the org config's
check-type/gating mechanism, and neither SHALL ever fail the PR workflow,
regardless of org configuration. When one or more findings exist, the check
SHALL emit exactly one non-blocking `::warning::` annotation naming the total
finding count and the managed-resource sync recovery action. It SHALL write
each individual finding to the GitHub step summary. They SHALL NOT be included
in the PR workflow's combined TL;DR report, since that report's contract is a
list of actions a developer must take before merge, and nothing a
tooling-currency check finds is required before merge.

#### Scenario: Drifted tooling never fails the workflow

- **GIVEN** the skills and tooling drift check finds every vendored module out
  of date
- **WHEN** the PR workflow's gating step runs
- **THEN** the workflow succeeds regardless — this finding has no bearing on the
  exit status

#### Scenario: Multiple findings produce one annotation

- **GIVEN** workflow-ref alignment and skills/tooling comparison produce four
  findings
- **WHEN** tooling currency reports the result
- **THEN** it emits one warning naming four findings and the sync recovery
  action, and the step summary lists all four findings

#### Scenario: Tooling-currency findings are absent from the combined report

- **GIVEN** the workflow-ref alignment check and the skills/tooling drift check
  both find drift
- **WHEN** the PR workflow's combined TL;DR report is built
- **THEN** neither finding appears in that report; they are reported separately
  as their own
  `::warning::` output

### Requirement: Local sync script

The template repo SHALL provide a script, runnable from an already-bootstrapped
child repo with no instance repo clone (`python3 -m panopticon.sync` or
equivalent), that reconciles complete managed resource directories from the
instance's current default branch. The script SHALL stage each managed directory
before applying it, so every module required by the refreshed sync entrypoint is
available together. It SHALL NOT use a per-module allowlist for the managed
`panopticon/` directory.

The script SHALL preserve protected child paths, including
`panopticon/config.json`, `panopticon/.gitignore`, and child-owned workflow
files. It SHALL create or refresh Panopticon-managed caller workflows from the
single shared caller contract and SHALL NOT overwrite or delete unrecognized
child workflow files. The script SHALL NOT delete any child-repository file,
including a managed resource that no longer exists in the instance source,
except exact receipt-owned artifacts retired by a disabled instance feature.
It SHALL delete those retired feature artifacts noninteractively, report each
deleted path, update the receipt, and never stage, commit, or push a deletion.

Given a `--check-updates` flag, the script SHALL run as a pure dry run: it SHALL
report every directory-derived resource that would change or be protected, using
content-based comparison, and SHALL NOT write any file.

#### Scenario: New sync dependency arrives with the managed directory

- **GIVEN** the instance adds a module required by a refreshed sync entrypoint
- **WHEN** local sync refreshes the managed `panopticon/` directory
- **THEN** the entrypoint and its new dependency are installed as one staged
  resource set before the refreshed entrypoint is used

#### Scenario: Default run refreshes a missing resource-sync caller

- **GIVEN** an initialized child lacks
  `.github/workflows/panopticon-resource-sync.yml`
- **WHEN** local sync runs without flags
- **THEN** it creates the generated caller without rerunning bootstrap

#### Scenario: Protected child workflow is retained

- **GIVEN** a child repository contains a workflow not managed by Panopticon
- **WHEN** local sync refreshes workflows
- **THEN** it does not modify or delete that workflow

#### Scenario: Removed instance resource remains in the child repository

- **GIVEN** a file previously synchronized into a managed directory is no
  longer present in the instance source and is not a receipt-owned retired
  feature artifact
- **WHEN** local sync runs
- **THEN** it does not delete that child file

#### Scenario: Disabled feature artifact is removed

- **GIVEN** a valid feature receipt identifies an OKF helper that the effective
  instance configuration no longer selects
- **WHEN** local sync runs without flags
- **THEN** it deletes that helper, reports the deleted path, and leaves
  unrelated child files untouched

#### Scenario: --check-updates writes nothing

- **WHEN** the sync script is run with `--check-updates`
- **THEN** it reports which files would change or be removed and exits without
  writing or deleting any file

#### Scenario: Nothing to sync

- **GIVEN** every skill and vendored tooling file in the child repo already
  matches the instance
  repo's current content
- **WHEN** the sync script runs (with or without `--check-updates`)
- **THEN** it reports that everything is current and makes no changes

#### Scenario: Invalid instance provider configuration fails before caller writes

- **GIVEN** the child can read its local configuration but the instance provider
  configuration is absent or invalid
- **WHEN** local sync runs
- **THEN** it exits with a configuration error and does not write managed caller
  workflows

### Requirement: Org-declared instance-level customization protection

The instance repo's `panopticon.config.json` SHALL support an org-declared
`protected_paths` field
listing paths (skills, vendored tooling modules, or other instance-repo content)
the org has
customized at the instance level and which SHALL NOT be overwritten by
`sync-from-template`'s pull
from the upstream template. This is distinct from the template-declared
protected-config registry
(`panopticon.diagram.config.json` and any future entries the template itself
declares): the org
maintains this list itself, and the template has no knowledge of it in advance.

Protection for these org-declared paths SHALL be applied via a mechanism that
requires no commit —
writing them, with the `merge=ours` attribute, to a location outside the tracked
working tree
(`.git/info/attributes` or equivalent) rather than to the tracked
`.gitattributes` file. Protecting
a *tracked* file via an uncommitted change to that same file is explicitly
insufficient: when the
incoming template merge also modifies that file, git refuses to proceed with the
merge at all
rather than silently ignoring the local uncommitted change — a failure mode this
requirement
exists specifically to avoid.

Because this protection is not visible in the tracked tree, the
`sync-from-template` workflow run
that applies it SHALL print, to the GitHub Actions step summary, which paths
were protected during
that run.

#### Scenario: Org-declared path survives a routine sync

- **GIVEN** the instance repo's `panopticon.config.json` lists a customized
  skill file in
  `protected_paths`, and the incoming template sync also modifies that same
  file's default content
- **WHEN** `sync-from-template` runs
- **THEN** the instance's customized version of that file is unchanged after the
  sync, and the sync
  completes without the merge aborting

#### Scenario: Org-declared path survives a first-time sync

- **GIVEN** an instance repo created via "Use this template" with a
  `protected_paths` entry for a
  file that also exists in the template with different content (a genuine
  same-path conflict)
- **WHEN** `sync-from-template` runs its first-time sync (`-X theirs`, no common
  ancestor)
- **THEN** the instance's version of that file wins, even though `-X theirs`
  would otherwise hand it
  to the template

#### Scenario: Protected paths are named in the step summary

- **GIVEN** `panopticon.config.json` lists one or more `protected_paths` entries
- **WHEN** `sync-from-template` runs
- **THEN** the GitHub Actions step summary names every path that was protected
  during that run

### Requirement: Shared child resource synchronization workflow

The template SHALL provide a reusable workflow that refreshes an initialized
child repository's managed Panopticon skills and vendored local tooling from its
configured instance repository. A child SHALL invoke it through a stable local
manual caller. When the refresh changes managed resources, the workflow SHALL
use its automation branch and update only an open automation-owned pull request
against the child default branch. When no such open pull request exists,
including when a prior automation pull request was merged or closed, the
workflow SHALL create a new automation-owned pull request against the child
default branch. When no resources differ, it SHALL succeed without creating a
branch or pull request.

#### Scenario: Manual resource sync updates an open reviewable pull request

- **GIVEN** an initialized child repository whose managed Panopticon resources
  differ from its instance repository
- **AND** an open automation-owned pull request exists for the resource-sync
  branch against the child default branch
- **WHEN** a maintainer runs the child resource-sync workflow from the child
  default branch
- **THEN** the workflow updates that open pull request with only the refreshed
  managed resources

#### Scenario: Manual resource sync creates a pull request after a prior one closes

- **GIVEN** an initialized child repository whose managed Panopticon resources
  differ from its instance repository
- **AND** the prior automation-owned pull request for the resource-sync branch
  was merged or closed
- **WHEN** a maintainer runs the child resource-sync workflow from the child
  default branch
- **THEN** the workflow creates a new pull request containing only the
  refreshed managed resources
- **AND** the workflow does not update the merged or closed pull request

#### Scenario: Current resources create no pull request

- **GIVEN** an initialized child repository whose managed Panopticon resources
  match its instance repository
- **WHEN** a maintainer runs the child resource-sync workflow from the child
  default branch
- **THEN** the workflow succeeds without creating a branch or pull request

#### Scenario: Non-default branch cannot use the instance credential

- **GIVEN** a resource-sync workflow dispatch targets a child branch other than
  the repository default branch
- **WHEN** the shared workflow begins
- **THEN** it fails before mapping or using the instance-read credential and
  does not create a pull request

### Requirement: Tooling-currency reads the authoritative instance manifest

The advisory tooling-currency check SHALL parse the versioned data-only
`panopticon/local-tooling.json` manifest from the already checked-out instance
repository. It SHALL validate the same schema and module-path constraints as
bootstrap and local sync, and SHALL compare only the manifest-listed child
tooling modules. It SHALL NOT execute manifest content or use a child manifest
copy.

#### Scenario: Instance manifest selects compared tooling

- **GIVEN** a child has a stale or absent manifest copy
- **WHEN** the PR workflow runs tooling-currency against an instance checkout
- **THEN** it determines managed tooling from the validated instance manifest
  and reports content drift only for those modules

#### Scenario: Invalid instance manifest remains advisory

- **GIVEN** the instance checkout contains an invalid local-tooling manifest
- **WHEN** tooling-currency runs
- **THEN** it emits a non-blocking warning naming the manifest error and does
  not write or delete child files

### Requirement: Tooling-currency identifies unmanaged Python tooling

The advisory tooling-currency check SHALL identify Python source paths under a
child's `panopticon/` directory that are outside the instance-owned
local-tooling manifest. It SHALL ignore child configuration, indexes,
`.gitignore`, and bytecode. A candidate also present in the instance checkout
but excluded from the manifest SHALL be reported as instance-excluded; every
other candidate SHALL be reported as child-only and unknown. These findings
SHALL remain non-blocking `::warning::` output and SHALL not alter files.

#### Scenario: Instance-excluded module is advisory

- **GIVEN** a child contains `panopticon/llm.py` and the instance checkout
  contains the same path outside the local-tooling manifest
- **WHEN** tooling-currency runs in the PR workflow
- **THEN** it emits a non-blocking warning classifying the module as
  instance-excluded

#### Scenario: Child-only module is advisory

- **GIVEN** a child contains `panopticon/legacy_child_module.py` that is absent
  from the instance checkout and the local-tooling manifest
- **WHEN** tooling-currency runs in the PR workflow
- **THEN** it emits a non-blocking warning classifying the module as child-only
  and unknown

#### Scenario: Child state is excluded from candidate detection

- **GIVEN** a child contains `panopticon/config.json`, `panopticon/index.json`,
  `.gitignore`, or bytecode
- **WHEN** tooling-currency runs in the PR workflow
- **THEN** it emits no unmanaged-tooling warning for that state file

### Requirement: Trusted instance-managed Bedrock action is automatically protected

Template sync SHALL derive the fixed
`.github/actions/panopticon-aws-credentials/action.yml` path when the raw
instance configuration selects provider `bedrock` and credential mode
`instance-managed`. It SHALL write that provider-derived path to runtime
`.git/info/attributes` using `merge.ours`, report it separately from generated
and organization-declared paths, and use the same derivation in local recovery
instructions. No configuration field SHALL replace the fixed path.

#### Scenario: Instance-managed action survives sync

- **GIVEN** the trusted raw contract selects Bedrock `instance-managed`
- **WHEN** template sync changes the fixed action path
- **THEN** the instance action remains unchanged and the summary identifies the
  provider-derived protected path

#### Scenario: Other modes do not protect the action

- **GIVEN** the instance is unconfigured, uses another provider, or uses
  Bedrock `github-oidc`
- **WHEN** template sync registers paths
- **THEN** it does not add the Bedrock action unless the organization explicitly
  lists it in `protected_paths`

### Requirement: Protected-path derivation tolerates non-object input

The deterministic protected-path derivation helper SHALL treat a non-object
instance configuration as an empty configuration and SHALL return generated
template paths without raising an attribute error.

#### Scenario: Invalid sync configuration remains safe to inspect

- **GIVEN** protected-path derivation receives a non-object value
- **WHEN** template sync prepares runtime merge attributes
- **THEN** it returns only generated template paths and continues to the
  existing provider-configuration validation boundary

### Requirement: Template sync automatically protects the fixed instance-managed credential action

The shared template-sync workflow SHALL derive
`.github/actions/panopticon-aws-credentials/action.yml` as a protected path
when the loaded instance configuration selects provider `bedrock` with
credential mode `instance-managed`. It SHALL write the derived path to the
runtime merge attributes using the existing `merge.ours` driver, report it
separately from organization-declared `protected_paths`, and apply the same
derivation in local recovery instructions. No configuration field SHALL be
able to replace the fixed path. Generated overlays SHALL emit compatible
protection metadata that classifies paths as template-generated,
provider-derived, or organization-declared. Only organization-declared
protected customizations SHALL require protected-path debt records.

#### Scenario: Instance-managed action survives routine template sync

- **GIVEN** an instance contract selects Bedrock `instance-managed` credentials
  and the incoming template changes the fixed action path
- **WHEN** shared template sync runs
- **THEN** the instance action remains unchanged, the merge completes, and the
  summary identifies the provider-derived protected path

#### Scenario: Generated protection is visible to review

- **GIVEN** a generated overlay contains an organization-declared protected path
- **WHEN** tooling-currency validation examines the overlay
- **THEN** it reports the path, ownership reason, and debt-removal condition
  separately from template-generated and provider-derived paths

#### Scenario: Provider-derived wrapper is not organization debt

- **GIVEN** a generated overlay selects Bedrock `instance-managed` credentials
- **WHEN** tooling-currency validation examines its protection metadata
- **THEN** it reports the fixed credential wrapper as provider-derived without
  requiring organization-debt ownership or removal fields

#### Scenario: Other provider modes do not protect the Bedrock action

- **GIVEN** the instance is unconfigured, uses another provider, or uses
  Bedrock `github-oidc`
- **WHEN** shared template sync registers protected paths
- **THEN** it does not add the Bedrock credential-action path unless the
  organization explicitly lists it in `protected_paths`

#### Scenario: Non-object configuration remains syncable

- **GIVEN** the protected-path derivation helper receives a non-object
  configuration value
- **WHEN** it derives runtime merge-protected paths
- **THEN** it returns only template-declared generated paths and does not raise
  an attribute error

#### Scenario: Local recovery matches hosted sync protection

- **GIVEN** hosted template sync fails before merging
- **WHEN** an owner follows the generated local recovery commands
- **THEN** the same provider-derived credential-action path is protected before
  the local merge

### Requirement: Template sync SHALL support a named template branch

The instance template-sync dispatch workflow SHALL accept a non-empty
`template_ref` input with `main` as its default and SHALL pass it to the shared
template-sync workflow. The shared workflow SHALL fetch and merge the named
ref from the fixed Panopticon template repository. It SHALL use that ref in
success and failure summaries and in local recovery instructions. Existing
callers that omit the reusable-workflow input SHALL continue to sync `main`.

#### Scenario: Maintainer tests a template branch

- **WHEN** a maintainer dispatches template sync from an instance test branch
  with `template_ref` set to a named template branch
- **THEN** the workflow fetches and merges that named template branch into the
  instance test branch and reports the selected ref

#### Scenario: Existing caller omits the template ref

- **WHEN** an existing instance caller invokes the shared workflow without a
  `template_ref` value
- **THEN** the shared workflow fetches and merges the template `main` branch

### Requirement: Template sync SHALL summarize changed paths

After a successful template sync merge, the shared workflow SHALL append a
dedicated Actions summary section listing every path whose resulting content
changed from the recorded pre-sync commit to `HEAD`. If the merge produces no
tree changes, the section SHALL explicitly state that no paths changed. The
summary SHALL also identify the selected template ref.

#### Scenario: Template merge updates managed files

- **WHEN** a template sync merge changes one or more files
- **THEN** the Actions summary identifies the selected ref and lists each
  changed repository-relative path

#### Scenario: Template is already current

- **WHEN** the selected template ref produces no tree changes
- **THEN** the Actions summary states that no paths changed
