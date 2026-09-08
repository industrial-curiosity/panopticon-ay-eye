# Tooling currency delta

## ADDED Requirements

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
