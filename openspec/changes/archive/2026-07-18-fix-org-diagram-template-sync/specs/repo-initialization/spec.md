# Repository Initialization Delta

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
   then push without requiring manual intervention, except for paths with an
   explicit `merge=ours` rule.
3. When a common ancestor **does** exist, use the default merge strategy and
   surface genuine conflicts with
   local-resolution instructions rather than overriding them silently, except
   for paths with an explicit
   `merge=ours` rule.
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
7. **Before** running the merge (steps 1–3 above), write every
   template-declared, instance-owned generated
   path, initially `docs/architecture.md`, with the `merge=ours` attribute to
   `.git/info/attributes`. This
   fixed list SHALL be owned by the template sync workflow, not read from
   protected JSON configuration and
   not read from org-declared `protected_paths`.
8. In the same pre-merge registration, read `panopticon.config.json`'s
   org-declared `protected_paths` field
   (tooling-currency capability) and write each listed path with the
   `merge=ours` attribute to
   `.git/info/attributes` — never to the tracked `.gitattributes` file, and
   without committing anything.
   This SHALL apply regardless of whether the incoming template changes touch
   the same paths, and MUST NOT
   cause the merge to abort or require manual intervention the way an
   uncommitted change to a tracked file
   the incoming merge also touches would.
9. Reuse the `merge.ours.driver true` configuration already registered for
   protected config and org-declared
   paths; the generated path SHALL NOT introduce another driver.
10. Print, to the GitHub Actions step summary, every path from `protected_paths`
    that was protected during
    that run — since org customization protection is not visible in the tracked
    tree, this is the only
    record of it for that run. The fixed generated path SHALL be identified
    separately and SHALL NOT be
    presented as an org customization.

Auto-resolution in case 2 is safe for ordinary template files because instance
repos created via "Use this
template" contain only files that originated from the template;
instance-specific files
(`panopticon.config.json`, org skills) do not exist in the template and are
therefore never overridden.
Registered protected-config paths (case 5) do exist in the template and hold
instance configuration.
Org-declared paths (case 8) may or may not exist in the template and represent
explicit customization.
`docs/architecture.md` also exists in the template, but only as a placeholder:
once present in an instance,
it is deterministic generated state owned by that instance and therefore follows
the fixed rule in case 7.

#### Scenario: First-time sync after "Use this template"

- **GIVEN** an instance repo created via GitHub's "Use this template" with no
  shared git history with the
  template
- **WHEN** the sync workflow runs
- **THEN** it detects the missing common ancestor, merges with `-X theirs`,
  applies explicit path merge
  attributes, and pushes without error

#### Scenario: Routine sync with common ancestor

- **GIVEN** an instance repo that has previously synced with the template and
  therefore has a common ancestor
- **WHEN** the sync workflow runs
- **THEN** it merges normally; divergence outside explicitly attributed paths
  surfaces as a conflict with
  local-resolution instructions

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

#### Scenario: Org-declared protected path survives even when the template touches the same path

- **GIVEN** `panopticon.config.json` lists a customized skill file in
  `protected_paths`, and the incoming
  template sync also modifies that same file's default content in this run
- **WHEN** the sync workflow runs
- **THEN** the instance's customized version is unchanged after the sync, the
  merge completes without
  aborting, and the tracked `.gitattributes` file merges normally

#### Scenario: Protected paths are visible in the step summary, not the tracked tree

- **GIVEN** `panopticon.config.json` lists one or more `protected_paths` entries
- **WHEN** the sync workflow runs
- **THEN** the GitHub Actions step summary names every org-declared protected
  path, distinguishes the fixed
  generated path from those customizations, and no tracked file records either
  runtime list

#### Scenario: Both sides independently add the org diagram during routine history

- **GIVEN** the instance and template share history from before
  `docs/architecture.md` existed, then each side
  independently adds that path with different content
- **WHEN** the routine template merge runs
- **THEN** the merge succeeds and retains the instance's generated
  `docs/architecture.md`

#### Scenario: Both sides modify the org diagram during routine history

- **GIVEN** the instance and template share an earlier `docs/architecture.md`,
  then each side modifies it
  independently
- **WHEN** the routine template merge runs
- **THEN** the merge succeeds and retains the instance's generated
  `docs/architecture.md`

#### Scenario: Unrelated histories both contain the org diagram

- **GIVEN** the instance and template have unrelated histories and each contains
  a different
  `docs/architecture.md`
- **WHEN** the first template sync runs with `--allow-unrelated-histories -X
  theirs`
- **THEN** the merge succeeds and retains the instance's generated file despite
  the general `theirs` strategy

#### Scenario: Missing instance diagram receives the template placeholder

- **GIVEN** the template contains its placeholder `docs/architecture.md` and the
  instance does not contain
  that path
- **WHEN** template sync runs
- **THEN** the placeholder is added to the instance because there is no existing
  instance-generated file to
  preserve
