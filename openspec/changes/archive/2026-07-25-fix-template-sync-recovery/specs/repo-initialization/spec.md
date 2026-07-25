# Repo initialization delta

## ADDED Requirements

### Requirement: Template sync registers effective protected-path attributes

Before every template merge, the shared template-sync workflow SHALL write a
separate physical `<path> merge=ours` line for each template-declared generated
path and each organization-declared `protected_paths` entry in
`.git/info/attributes`. It SHALL use the existing `merge.ours.driver true`
configuration, and the local recovery commands SHALL write equivalent valid
attribute lines before attempting their merge.

#### Scenario: Both sides modify an instance-owned generated path

- **GIVEN** the instance and template share an earlier `docs/architecture.md`
  and both have modified it since that point
- **WHEN** the shared template-sync workflow registers protection and merges the
  template
- **THEN** Git applies the `ours` merge driver, the merge completes without a
  conflict for that path, and the instance version remains unchanged

#### Scenario: Local recovery registers an organization-declared path

- **GIVEN** a failed sync's local recovery commands run in an instance whose
  `protected_paths` contains a customized template-managed file
- **WHEN** the commands create `.git/info/attributes` before the merge
- **THEN** the file contains a separate valid `merge=ours` line for that path
  and the equivalent local merge preserves the instance version

## MODIFIED Requirements

### Requirement: Template sync uses a shared repairable workflow

The instance `sync-from-template.yml` SHALL be a minimal, fixed caller that
invokes only the template-owned reusable workflow
`.github/workflows/shared-template-sync-caller-only.yml` from
`industrial-curiosity/panopticon-ay-eye@main`. The shared workflow SHALL check
out and update the calling instance repository, retain the
`PANOPTICON_INSTANCE_TOKEN` fallback and pre-push validation contract, and keep
all merge, protected-path, and recovery logic in the template repository. The
instance caller SHALL not duplicate that logic or accept a configurable
repository, workflow path, or ref. It SHALL pass the optional instance-token
secret explicitly and SHALL NOT expose either token value.

On every sync failure, the stage that detects the failure SHALL write a valid
Markdown step-summary section that names the failed stage, records the detected
error, and states the relevant corrective action before the workflow exits. The
shared workflow SHALL also provide a valid-Markdown local-recovery section with
commands for a local clone of the instance repository to fetch the fixed
template remote, register equivalent protected-path attributes, perform the
equivalent merge, resolve any conflict, review the result, commit, and push.
The shared workflow filename SHALL identify it as shared and caller-only, and it
SHALL accept only `workflow_call` rather than a direct trigger.

User-facing documentation SHALL explain that the sync preserves every exact path
listed in `protected_paths`, the protected diagram configuration, and an
existing generated `docs/architecture.md`. It SHALL also explain that other
customized template-managed files can receive a template update or produce a
merge conflict, and that `protected_paths` does not protect child-repository
files from `python3 -m panopticon.sync`.

#### Scenario: Shared sync logic is fixed after an instance is created

- **GIVEN** an instance contains the minimal sync caller
- **WHEN** the template fixes its shared reusable sync workflow
- **THEN** the instance's next sync run uses the fixed workflow without copying
  workflow code into the instance

#### Scenario: Ordinary template update without an instance token

- **GIVEN** `PANOPTICON_INSTANCE_TOKEN` is not configured
- **WHEN** the shared workflow merges changes outside `.github/workflows/`
- **THEN** it pushes the update using the default GitHub token

#### Scenario: Workflow update without an instance token

- **GIVEN** `PANOPTICON_INSTANCE_TOKEN` is not configured
- **WHEN** the shared workflow merges a change under `.github/workflows/`
- **THEN** it does not push, emits a concise error, and writes setup
  instructions for a GitHub token secret with Contents and Workflows read/write
  permission

#### Scenario: Merge failure identifies its cause and recovery

- **WHEN** the shared sync workflow's template merge fails
- **THEN** its step summary renders Markdown, names the merge stage, includes
  the detected Git error and a corrective action, and contains valid local
  recovery commands with the fixed template remote, protected-path setup,
  equivalent merge, conflict-resolution, review, commit, and push steps

#### Scenario: Shared sync caller cannot be redirected

- **WHEN** instance configuration or workflow-dispatch input attempts to select
  another sync repository, workflow path, or ref
- **THEN** the caller rejects the unsupported configuration and invokes no
  alternative workflow

#### Scenario: Shared workflow is not directly runnable

- **WHEN** a user views the template workflow list
- **THEN** the shared workflow is named `shared-template-sync-caller-only.yml`
  and has no direct trigger such as `workflow_dispatch`

#### Scenario: Maintainer protects an instance customization

- **GIVEN** an instance customizes a template-managed skill or workflow
- **WHEN** its maintainer adds that exact path to `protected_paths` and runs the
  template sync
- **THEN** the sync preserves the instance copy and the setup documentation
  explains that the same setting does not protect child-repository tooling syncs

#### Scenario: Maintainer has an unprotected instance customization

- **GIVEN** an instance customizes a template-managed file that is absent from
  `protected_paths`
- **WHEN** the template also changes that file during sync
- **THEN** the setup documentation explains that Git may update the file or
  report a merge conflict for local resolution
