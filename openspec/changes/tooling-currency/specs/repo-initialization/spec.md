## MODIFIED Requirements

### Requirement: Template update workflow

> Note: this requirement's baseline already reflects the `architecture-diagrams` change's
> protected-config mechanism (points 5–6 below), which is implemented and complete but not yet
> archived into `openspec/specs/` at the time this delta was written. This delta's full content
> below is accurate to the actual current behavior of `sync-from-template.yml`.

The template repo SHALL ship a `sync-from-template.yml` workflow that instance repo owners can trigger
manually to pull upstream template changes. The workflow SHALL:

1. Detect whether the instance repo shares git history with the template (i.e., a common ancestor exists).
2. When **no common ancestor exists** (first-time sync after "Use this template" which creates unrelated
   histories), automatically resolve all add/add conflicts by preferring the template version (`-X theirs`),
   then push without requiring manual intervention.
3. When a common ancestor **does** exist, use the default merge strategy and surface genuine conflicts with
   local-resolution instructions rather than overriding them silently.
4. Use a fine-grained PAT with Contents R/W (not `GITHUB_TOKEN`) for git operations — GitHub unconditionally
   rejects pushes to `.github/workflows/` from `GITHUB_TOKEN` regardless of job-level permissions. The
   workflow SHALL use `PANOPTICON_INSTANCE_TOKEN` (already scoped to the instance repo with Contents R/W)
   via `actions/checkout token:` so that `git push` inherits it.
5. Exclude every path listed in the template's protected-config registry from the merge, so the instance's
   version of each registered file always wins regardless of what the template ships or how cases 2 and 3
   above would otherwise resolve it.
6. For each registered protected-config path present in both the incoming template version and the instance's
   current file, compare their top-level JSON field names and emit a non-blocking `::warning::` naming the
   file and which fields the template added or removed that the instance's copy doesn't have, so instance
   owners notice new or deprecated configuration options without them being silently applied or silently
   missed.
7. **Before** running the merge (steps 1–3 above), read `panopticon.config.json`'s org-declared
   `protected_paths` field (tooling-currency capability) and write each listed path, with the
   `merge=ours` attribute, to `.git/info/attributes` — never to the tracked `.gitattributes` file,
   and without committing anything. This SHALL apply regardless of whether the incoming template
   changes touch the same paths, and MUST NOT cause the merge to abort or require manual
   intervention the way an uncommitted change to a *tracked* file the incoming merge also touches
   would.
8. Print, to the GitHub Actions step summary, every path from `protected_paths` that was protected
   during that run — since this protection is not visible in the tracked tree, this is the only
   record of it for that run.

Auto-resolution in case 2 is safe because instance repos created via "Use this template" contain only
files that originated from the template; instance-specific files (`panopticon.config.json`, org skills)
do not exist in the template and are therefore never overridden. Registered protected-config paths (case 5)
DO exist in the template (each with a template-shipped default), which is exactly why they need explicit
protection rather than relying on case 2's "doesn't exist upstream" reasoning. Org-declared paths (cases
7–8) may or may not exist in the template — the mechanism protects them either way, since the org, not
the template, decides what belongs in `protected_paths`.

#### Scenario: First-time sync after "Use this template"

- **GIVEN** an instance repo created via GitHub's "Use this template" (no shared git history with the template)
- **WHEN** the sync workflow runs
- **THEN** it detects the missing common ancestor, merges with `-X theirs`, and pushes without error

#### Scenario: Routine sync with common ancestor

- **GIVEN** an instance repo that has previously synced with the template (common ancestor exists)
- **WHEN** the sync workflow runs
- **THEN** it merges normally; any genuine divergence surfaces as a conflict with local-resolution instructions

#### Scenario: Protected config survives a template change

- **GIVEN** an instance repo whose `panopticon.diagram.config.json` sets a non-default `format`, and the
  template has since changed its own shipped default for that file
- **WHEN** the sync workflow runs
- **THEN** the instance's `panopticon.diagram.config.json` is unchanged after sync — the merge never applies
  the template's version to this path

#### Scenario: Sync warns when the template adds a new protected-config field

- **GIVEN** the template's registered version of a protected-config file gains a new top-level field not
  present in the instance's current copy
- **WHEN** the sync workflow runs
- **THEN** the workflow succeeds and emits a warning naming the file and the new field, without modifying the
  instance's file

#### Scenario: Org-declared protected path survives even when the template touches the same path

- **GIVEN** `panopticon.config.json` lists a customized skill file in `protected_paths`, and the
  incoming template sync also modifies that same file's default content in this run
- **WHEN** the sync workflow runs
- **THEN** the instance's customized version is unchanged after the sync, the merge completes without
  aborting, and the tracked `.gitattributes` file (unaffected by `protected_paths`) merges normally

#### Scenario: Protected paths are visible in the step summary, not the tracked tree

- **GIVEN** `panopticon.config.json` lists one or more `protected_paths` entries
- **WHEN** the sync workflow runs
- **THEN** the GitHub Actions step summary for that run names every protected path, and no tracked
  file in the instance repo records this list

### Requirement: Local tooling package vendored into child repo

The bootstrap script SHALL download the local-tooling subset of the `panopticon` Python package —
the modules that Phase 2 skills and the Phase 3 finalization command invoke directly
(`__init__.py`, `config.py`, `docs.py`, `index.py`, `init_repo.py`), plus the local sync script
(tooling-currency capability) that lets an already-initialized repo pull the instance's current
skills and tooling on demand — from the instance repo and write them to the child repo's
`panopticon/` directory, creating it if absent, so `python3 -m panopticon.docs`,
`python3 -m panopticon.init_repo`, and `python3 -m panopticon.sync` are all runnable immediately
after Phase 1 with no manual setup: no cloning the instance repo, no `PYTHONPATH` configuration, no
other local Python environment step.

Modules used only by the reusable GitHub Actions workflows that check out the instance repo directly
(`llm.py`, `drift.py`, `currency.py`, `merge.py`, `extraction.py`, `skills.py`, `bootstrap.py`, `diagrams.py`,
`diagram_check.py`, and the `parsers/` package) SHALL NOT be written to the child repo — they have no role
in local Phase 2/3 work and bootstrap.py's own comment already documents this CI-only split.

Because the vendored subset and the instance repo's full package share the same `panopticon` package
name, any CI workflow step that checks out both the child repo (as its working directory) and the
instance repo (added to `PYTHONPATH`) in the same job SHALL guarantee that CI-only modules resolve from
the instance repo, not from the child repo's vendored subset. The workflow MUST NOT rely on `PYTHONPATH`
ordering alone to win this resolution, since `python3 -m`/`-c` prepend the current working directory to
`sys.path` ahead of `PYTHONPATH` entries.

#### Scenario: Local tooling is usable immediately after bootstrap

- **GIVEN** a freshly bootstrapped child repo that has never had the `panopticon` package locally before
- **WHEN** the user's agent follows the `panopticon-doc-generation` skill's instructions to run
  `python3 -m panopticon.docs render ...`
- **THEN** the command runs successfully without the user cloning the instance repo or configuring
  `PYTHONPATH`

#### Scenario: The sync script is usable immediately after bootstrap

- **GIVEN** a freshly bootstrapped child repo
- **WHEN** the user runs `python3 -m panopticon.sync --check-updates`
- **THEN** the command runs successfully with no instance repo clone or `PYTHONPATH` configuration

#### Scenario: CI-only modules are excluded

- **WHEN** the bootstrap script vendors the local-tooling subset
- **THEN** the child repo's `panopticon/` directory contains `__init__.py`, `config.py`, `docs.py`,
  `index.py`, `init_repo.py`, and `sync.py`, and none of `llm.py`, `drift.py`, `currency.py`, `merge.py`,
  `extraction.py`, `skills.py`, `bootstrap.py`, `diagrams.py`, `diagram_check.py`, or `parsers/`

#### Scenario: Re-run refreshes vendored modules in place

- **WHEN** the bootstrap script runs again on a repo that already has the vendored `panopticon/` modules
- **THEN** each of the six files is overwritten in place with the instance repo's current content, and
  no duplicate files are created

#### Scenario: CI resolves instance-only modules despite child vendoring

- **GIVEN** a child repo whose vendored `panopticon/` directory contains only the local-tooling subset,
  checked out alongside the instance repo in the same CI job with `PYTHONPATH` pointing at the instance
  repo
- **WHEN** a workflow step runs `python3 -m panopticon.drift` (or any other CI-only module)
- **THEN** the instance repo's copy of the module runs, and the command MUST NOT fail with "No module
  named panopticon.<module>" due to the child repo's partial subset shadowing it
