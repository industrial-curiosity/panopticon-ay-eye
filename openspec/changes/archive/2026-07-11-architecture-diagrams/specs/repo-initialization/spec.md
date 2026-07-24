# Repo Initialization Spec

## MODIFIED Requirements

### Requirement: Template update workflow

The template repo SHALL ship a `sync-from-template.yml` workflow that instance
repo owners can trigger
manually to pull upstream template changes. The workflow SHALL:

1. Detect whether the instance repo shares git history with the template (i.e.,
   a common ancestor exists).
2. When **no common ancestor exists** (first-time sync after "Use this template"
   which creates unrelated
   histories), automatically resolve all add/add conflicts by preferring the
   template version (`-X theirs`),
   then push without requiring manual intervention.
3. When a common ancestor **does** exist, use the default merge strategy and
   surface genuine conflicts with
   local-resolution instructions rather than overriding them silently.
4. Use a fine-grained PAT with Contents R/W (not `GITHUB_TOKEN`) for git
   operations — GitHub unconditionally
   rejects pushes to `.github/workflows/` from `GITHUB_TOKEN` regardless of
   job-level permissions. The
   workflow SHALL use `PANOPTICON_INSTANCE_TOKEN` (already scoped to the
   instance repo with Contents R/W)
   via `actions/checkout token:` so that `git push` inherits it.
5. Exclude every path listed in the template's protected-config registry from
   the merge, so the instance's
   version of each registered file always wins regardless of what the template
   ships or how cases 2 and 3
   above would otherwise resolve it.
6. For each registered protected-config path present in both the incoming
   template version and the instance's
   current file, compare their top-level JSON field names and emit a
   non-blocking `::warning::` naming the
   file and which fields the template added or removed that the instance's copy
   doesn't have, so instance
   owners notice new or deprecated configuration options without them being
   silently applied or silently
   missed.

Auto-resolution in case 2 is safe because instance repos created via "Use this
template" contain only
files that originated from the template; instance-specific files
(`panopticon.config.json`, org skills)
do not exist in the template and are therefore never overridden. Registered
protected-config paths (case 5)
DO exist in the template (each with a template-shipped default), which is
exactly why they need explicit
protection rather than relying on case 2's "doesn't exist upstream" reasoning.

#### Scenario: First-time sync after "Use this template"

- **GIVEN** an instance repo created via GitHub's "Use this template" (no shared
  git history with the template)
- **WHEN** the sync workflow runs
- **THEN** it detects the missing common ancestor, merges with `-X theirs`, and
  pushes without error

#### Scenario: Routine sync with common ancestor

- **GIVEN** an instance repo that has previously synced with the template
  (common ancestor exists)
- **WHEN** the sync workflow runs
- **THEN** it merges normally; any genuine divergence surfaces as a conflict
  with local-resolution instructions

#### Scenario: Protected config survives a template change

- **GIVEN** an instance repo whose `panopticon.diagram.config.json` sets a
  non-default `format`, and the
  template has since changed its own shipped default for that file
- **WHEN** the sync workflow runs
- **THEN** the instance's `panopticon.diagram.config.json` is unchanged after
  sync — the merge never applies
  the template's version to this path

#### Scenario: Sync warns when the template adds a new protected-config field

- **GIVEN** the template's registered version of a protected-config file gains a
  new top-level field not
  present in the instance's current copy
- **WHEN** the sync workflow runs
- **THEN** the workflow succeeds and emits a warning naming the file and the new
  field, without modifying the
  instance's file
