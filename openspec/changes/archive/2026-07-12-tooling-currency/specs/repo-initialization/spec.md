# Repo Initialization Spec

## ADDED Requirements

### Requirement: Getting-started guide vendored into child repo

The bootstrap script SHALL download a single, concise getting-started guide from
the instance repo and
write it to the child repo's root as `PANOPTICON.md`, so a maintainer opening
the repo sees it
immediately without navigating into `docs/` or `.agents/skills/`. The guide's
content SHALL be static and
template-authored — downloaded verbatim, identical across every child repo of a
given instance, never
per-repo generated or agent-written — mirroring how skills and vendored tooling
modules are downloaded
as-is rather than templated. Re-running the bootstrap script SHALL overwrite
`PANOPTICON.md` in place,
the same idempotent-overwrite trust model already used for skills and vendored
tooling.

The guide SHALL, at minimum, describe: (1) the three repo roles (template,
instance, child) and the
pull-request/merge lifecycle in brief, so a new maintainer has the same
orientation the setup guide gives
an org owner; (2) where architecture diagrams live — this repo's own `##
Architecture diagram` section
in its `architecture.md`, and the org-wide diagram at the instance repo's
`docs/architecture.md`; and
(3) exactly how to keep this repo's skills and vendored tooling current — the
literal
`python3 -m panopticon.sync` and `python3 -m panopticon.sync --check-updates`
commands (tooling-currency
capability).

#### Scenario: Getting-started guide is downloaded on first bootstrap

- **WHEN** the bootstrap script runs in a child repo for the first time
- **THEN** the child repo's root contains `PANOPTICON.md`, downloaded from the
  instance repo

#### Scenario: Getting-started guide is refreshed on re-run

- **WHEN** the bootstrap script runs again on an already-bootstrapped repo
- **THEN** `PANOPTICON.md` is overwritten in place with the instance repo's
  current content, and no
  duplicate file is created

#### Scenario: Guide documents the sync command

- **WHEN** a maintainer reads `PANOPTICON.md`
- **THEN** it contains the literal command `python3 -m panopticon.sync` and
  explains that it pulls the
  instance repo's current skills and vendored tooling into this repo

#### Scenario: Guide points to both diagram locations

- **WHEN** a maintainer reads `PANOPTICON.md` looking for architecture diagrams
- **THEN** it names both this repo's own `## Architecture diagram` section and
  the instance repo's
  org-wide `docs/architecture.md`

### Requirement: Bootstrap output references the sync workflow and getting-started guide

The bootstrap script's printed output SHALL, on every run — first bootstrap and
idempotent re-run
alike — explicitly name `PANOPTICON.md`'s location and the literal `python3 -m
panopticon.sync` command
(including its `--check-updates` dry-run flag), so a maintainer discovers the
sync workflow directly from
the terminal output without first having to know `PANOPTICON.md` exists or read
source code. This output
is distinct from the `/panopticon-init` agent prompt (see "Agent prompts
output") — it SHALL be present
regardless of whether that prompt is also printed.

#### Scenario: First run prints the sync command and guide location

- **WHEN** the bootstrap script completes a first-time run
- **THEN** its output contains both `PANOPTICON.md` and the literal text
  `python3 -m panopticon.sync`

#### Scenario: Re-run also prints the sync command and guide location

- **WHEN** the bootstrap script is run again on an already-bootstrapped repo
- **THEN** its output still contains both `PANOPTICON.md` and `python3 -m
  panopticon.sync` — this is not
  gated behind "first run only", since a maintainer re-running the script
  specifically to pick up a
  tooling-currency fix needs to see it every time

### Requirement: Recorded instance_default_branch is resolved deterministically, never guessed

`instance_default_branch` SHALL be resolved via the same GitHub API
token/transport mechanism the
bootstrap script already uses for every other instance-repo request
(`GH_TOKEN`/`GITHUB_TOKEN`
environment variables, falling back to `gh auth token` only to extract a token —
never a direct `gh
api` subprocess call, which depends on the separate, narrower precondition of
`gh auth login` having
been run interactively, and can fail even when the token-based mechanism the
rest of bootstrap
already relies on works fine). Resolution SHALL NOT hardcode `"main"`, derive
the value from
`workflow_ref`, or otherwise guess it. `workflow_ref` MAY reference an
org-pinned tag or branch
chosen independently of the instance repo's actual default branch (see "Default
workflow ref
requires no manual instance setup"), so conflating the two would silently
produce a wrong value for
anything built from `instance_default_branch` (the tooling-currency capability's
org-diagram link
script). This mirrors "Recorded workflow_ref matches the wired caller
workflows"'s never-guess
discipline, applied to this second, independently-resolved field on the same
config file.

Both the bootstrap script (see "Bootstrap script refreshes
instance_default_branch on rerun") and
the finalization step use this same resolution logic — sharing the mechanism,
not the code path,
since bootstrap.py and init_repo.py cannot import from each other
(repo-initialization's existing
CI/local module boundary: init_repo.py is vendored into child repos and cannot
import bootstrap.py,
which is CI-only and never vendored).

#### Scenario: Instance's default branch is recorded as-is

- **GIVEN** the instance repo's actual default branch is `main`, and `GH_TOKEN`
  or `GITHUB_TOKEN` is
  set (or `gh auth token` yields a valid token)
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `instance_default_branch` field is `main`

#### Scenario: Non-standard default branch name is recorded, not overridden

- **GIVEN** the instance repo's actual default branch is `trunk`
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `instance_default_branch` field is `trunk`, not `main`

#### Scenario: workflow_ref and instance_default_branch are resolved independently

- **GIVEN** the org has pinned `workflow_ref` to `v2` in
  `panopticon.config.json`, and the instance
  repo's actual default branch is `main`
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** `workflow_ref` is `v2` and `instance_default_branch` is `main` — the
  two fields are never
  conflated or derived from one another

#### Scenario: A working GH_TOKEN resolves the branch even when `gh auth login` was never run

- **GIVEN** `GH_TOKEN` is set to a valid token, and the `gh` CLI is installed
  but has never had `gh
  auth login` run (so `gh api ...` would fail with an authentication error if
  called directly)
- **WHEN** the finalization step (or the bootstrap script, on a rerun of an
  already-initialized
  repo) resolves `instance_default_branch`
- **THEN** resolution succeeds, using `GH_TOKEN` directly rather than depending
  on `gh`'s own
  separate credential store

### Requirement: Bootstrap script refreshes instance_default_branch on rerun

The bootstrap script SHALL, on an already-initialized repo (one whose
`panopticon/config.json`
already exists), re-resolve `instance_default_branch` (same mechanism and
never-guess
discipline as "Recorded instance_default_branch is resolved deterministically,
never guessed") and
update just that field in `panopticon/config.json` in place, leaving every other
field untouched.
This is a narrow, explicit exception to "Bootstrap installer script"'s general
rule that the
bootstrap script SHALL NOT write `panopticon/config.json`: that rule protects
the file's *creation*
(gated on the finalization step's validation passing, so the file's existence is
a trustworthy signal
of "initialization complete") — it was never a statement that the file can never
be touched again.
Re-running the bootstrap script is a low-friction, frequently-repeated operation
(`PANOPTICON.md`
itself says "Re-run install.py to update") — refreshing this one field there,
rather than requiring a
full re-run of finalization (which in turn requires re-running the AI agent), is
the appropriate
place for this specific fix to land quickly.

The bootstrap script SHALL still never *create* `panopticon/config.json` — this
exception applies
only when the file already exists. On a repo's first bootstrap (config not yet
created), resolution
happens the first time via the finalization step, as already specified.

#### Scenario: Rerun on an initialized repo updates only instance_default_branch

- **GIVEN** an already-initialized child repo whose `panopticon/config.json` has
  `instance_default_branch: null` or missing (e.g. finalization couldn't resolve
  it originally)
- **WHEN** the bootstrap script is re-run and can now resolve the instance's
  default branch
- **THEN** `panopticon/config.json`'s `instance_default_branch` field is updated
  in place, and every
  other field (`repo`, `instance`, `workflow_ref`, `docs_location`) is unchanged

#### Scenario: First bootstrap on an uninitialized repo does not create panopticon/config.json

- **GIVEN** a child repo with no `panopticon/config.json` yet (never
  initialized)
- **WHEN** the bootstrap script runs
- **THEN** `panopticon/config.json` is still not created — only the finalization
  step, after
  validation passes, creates it (see "Bootstrap installer script")

## MODIFIED Requirements

### Requirement: Initialization finalization

A finalization command, distinct from the bootstrap script, SHALL validate the
agent-produced
documentation and index and write `panopticon/config.json` only when validation
passes. It SHALL read
the documentation location from the child repo (adopting an existing docs folder
or using the default
`docs/`), record it in the config along with `instance_default_branch` (see
"Recorded
instance_default_branch is resolved deterministically, never guessed"), and
verify org-level CI
prerequisites (report-only). The finalization step SHALL be idempotent:
re-running it updates the config
in place.

#### Scenario: Validation passes

- **WHEN** all four documentation layers are present and the local index is
  schema-valid
- **THEN** `panopticon/config.json` is written with `repo`, `instance`,
  `workflow_ref`, `docs_location`,
  and `instance_default_branch` fields

#### Scenario: Re-finalization after a docs update

- **WHEN** the finalization step is run again on an already-initialized repo
- **THEN** `panopticon/config.json` is updated in place and no duplicate files
  are created

### Requirement: Bootstrap installer script

The template repo SHALL include a Python bootstrap script that can be run
directly from a child repo
without cloning the instance repo locally, invoked via:

```text
curl -fsSL https://raw.githubusercontent.com/<instance>/main/install.py | python3
```

or equivalently by downloading and running it. The script SHALL read the
instance org/repo slug from the
`PANOPTICON_INSTANCE` environment variable, falling back to an interactive
prompt when the variable is not
set and stdin is a terminal. Using only Python stdlib and the GitHub API (no
additional dependencies), the
script SHALL:

1. Determine the child repo's skills location (see "Skills location selection")
   — this SHALL happen
   before any skill files are downloaded.
2. Download only skills whose directory name begins with `panopticon-` from the
   instance repo's
   `.agents/skills/` directory and write them to the chosen skills location in
   the child repo, creating
   the directory if absent. Skills at other name prefixes (org-internal skills,
   tooling skills, etc.)
   SHALL NOT be written to the child repo.
3. Download the local-tooling subset of the `panopticon` Python package into the
   child repo's
   `panopticon/` directory (see "Local tooling package vendored into child
   repo").
4. Download the getting-started guide from the instance repo and write it to the
   child repo's root as
   `PANOPTICON.md` (see "Getting-started guide vendored into child repo").
5. Download the three caller workflow files from the instance repo and write
   them to the child repo's
   `.github/workflows/`, creating the directory if absent.
6. If `panopticon/config.json` already exists (the repo was already
   initialized), re-resolve and
   update its `instance_default_branch` field in place (see "Bootstrap script
   refreshes
   instance_default_branch on rerun") — every other field is left untouched.
7. Verify org-level CI prerequisites (secrets and variables) and report any
   missing items — report-only,
   never blocking.
8. Output the exact prompts the user shall give their AI agent to complete the
   AI-dependent initialization
   steps (see "Agent prompts output"), and the sync-workflow reference (see
   "Bootstrap output references
   the sync workflow and getting-started guide").

The bootstrap script SHALL NOT *create* `panopticon/config.json` — that remains
the last artifact
created, by the finalization step, only after the agent has completed its work
and validation
passes. Step 6 above is a narrow, explicit exception covering only an update to
one field of an
*already-existing* config file on rerun (see "Bootstrap script refreshes
instance_default_branch on
rerun"); it does not change when or how the file is first created.

#### Self-bootstrapping when piped via curl

When `install.py` is piped from the instance repo via `curl | python3`, it runs
outside the instance repo
directory and cannot import the `panopticon` package locally. The script SHALL
detect this condition
(import failure at startup) and self-bootstrap by downloading
`panopticon/__init__.py` and
`panopticon/bootstrap.py` from the instance repo via the GitHub API, installing
them into `sys.modules`
in-process, then continuing with the normal import flow — without requiring any
local clone of the
instance repo.

Token discovery for GitHub API calls SHALL follow the same precedence used by
bootstrap.py: `GH_TOKEN`
env var, then `GITHUB_TOKEN` env var, then `gh auth token` if the `gh` CLI is
available. When no token is
found the API call is made unauthenticated (suitable for public instance repos;
private repos will receive
a 404 and the script SHALL exit with a clear error).

#### Scenario: Only panopticon-prefixed skills are installed

- **GIVEN** the instance repo's `.agents/skills/` contains both
  `panopticon-doc-generation/` and
  `openspec-apply-change/` (an org-internal skill), and the chosen skills
  location is `.agents/skills/`
  (the default)
- **WHEN** the bootstrap script runs
- **THEN** `.agents/skills/panopticon-doc-generation/` is written to the child
  repo and
  `.agents/skills/openspec-apply-change/` is not

#### Scenario: First run in an uninitialised repo

- **WHEN** the bootstrap script runs in a child repo with
  `PANOPTICON_INSTANCE=acme/panopticon-instance`
  set (or entered at the prompt), and the skills location prompt is accepted at
  its `.agents/skills/`
  default
- **THEN** the child repo's `.agents/skills/` contains the instance skills,
  `.github/workflows/` contains
  the three Panopticon caller workflows, the repo root contains `PANOPTICON.md`,
  and the terminal prints
  the `/panopticon-init` prompt — without creating `panopticon/config.json`

#### Scenario: Piped curl execution with panopticon package unavailable

- **GIVEN** the user runs `curl -fsSL
  https://raw.githubusercontent.com/<instance>/main/install.py | python3`
  from a child repo that does not contain the `panopticon` package
- **WHEN** the initial import of `panopticon.bootstrap` fails with
  `ModuleNotFoundError`
- **THEN** the script downloads `panopticon/__init__.py` and
  `panopticon/bootstrap.py` from the instance
  repo, installs them in-process, and proceeds identically to a local run with
  no error surfaced to the
  user

#### Scenario: Piped curl execution with PANOPTICON_INSTANCE unset

- **GIVEN** the user pipes `install.py` via curl without setting
  `PANOPTICON_INSTANCE`
- **WHEN** stdin is not a terminal (no interactive prompt possible)
- **THEN** the script exits with a non-zero code and a message that names the
  missing env var and shows
  the correct export-and-pipe command

#### Scenario: Instance slug not configured in interactive mode

- **WHEN** the bootstrap script runs with no `PANOPTICON_INSTANCE` env var and
  stdin is a terminal
- **THEN** the script prompts for the slug and proceeds using the entered value,
  identical to supplying
  the env var

#### Scenario: Re-run on an already-bootstrapped repo

- **WHEN** the bootstrap script is run again on a repo whose skills and
  workflows are already installed
- **THEN** all files are updated in place and nothing is duplicated

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
7. **Before** running the merge (steps 1–3 above), read
   `panopticon.config.json`'s org-declared
   `protected_paths` field (tooling-currency capability) and write each listed
   path, with the
   `merge=ours` attribute, to `.git/info/attributes` — never to the tracked
   `.gitattributes` file,
   and without committing anything. This SHALL apply regardless of whether the
   incoming template
   changes touch the same paths, and MUST NOT cause the merge to abort or
   require manual
   intervention the way an uncommitted change to a *tracked* file the incoming
   merge also touches
   would.
8. Print, to the GitHub Actions step summary, every path from `protected_paths`
   that was protected
   during that run — since this protection is not visible in the tracked tree,
   this is the only
   record of it for that run.

Auto-resolution in case 2 is safe because instance repos created via "Use this
template" contain only
files that originated from the template; instance-specific files
(`panopticon.config.json`, org skills)
do not exist in the template and are therefore never overridden. Registered
protected-config paths (case 5)
DO exist in the template (each with a template-shipped default), which is
exactly why they need explicit
protection rather than relying on case 2's "doesn't exist upstream" reasoning.
Org-declared paths (cases
7–8) may or may not exist in the template — the mechanism protects them either
way, since the org, not
the template, decides what belongs in `protected_paths`.

> Note: this requirement's baseline already reflects the `architecture-diagrams` change's
> protected-config mechanism (points 5–6 above), which is implemented and complete but not yet
> archived into `openspec/specs/` at the time this delta was written. This delta's full content
> above is accurate to the actual current behavior of `sync-from-template.yml`.

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

#### Scenario: Org-declared protected path survives even when the template touches the same path

- **GIVEN** `panopticon.config.json` lists a customized skill file in
  `protected_paths`, and the
  incoming template sync also modifies that same file's default content in this
  run
- **WHEN** the sync workflow runs
- **THEN** the instance's customized version is unchanged after the sync, the
  merge completes without
  aborting, and the tracked `.gitattributes` file (unaffected by
  `protected_paths`) merges normally

#### Scenario: Protected paths are visible in the step summary, not the tracked tree

- **GIVEN** `panopticon.config.json` lists one or more `protected_paths` entries
- **WHEN** the sync workflow runs
- **THEN** the GitHub Actions step summary for that run names every protected
  path, and no tracked
  file in the instance repo records this list

### Requirement: Local tooling package vendored into child repo

The bootstrap script SHALL download the local-tooling subset of the `panopticon`
Python package —
the modules that Phase 2 skills and the Phase 3 finalization command invoke
directly
(`__init__.py`, `config.py`, `docs.py`, `index.py`, `init_repo.py`), plus the
local sync script
(tooling-currency capability) that lets an already-initialized repo pull the
instance's current
skills and tooling on demand, plus the org-diagram link script
(architecture-diagrams capability,
"Org-diagram link script") that prints a resolvable link to this repo's section
of the org diagram —
from the instance repo and write them to the child repo's `panopticon/`
directory, creating it if
absent, so `python3 -m panopticon.docs`, `python3 -m panopticon.init_repo`,
`python3 -m panopticon.sync`, and `python3 -m panopticon.org_diagram_link` are
all runnable
immediately after Phase 1 with no manual setup: no cloning the instance repo, no
`PYTHONPATH`
configuration, no other local Python environment step.

Modules used only by the reusable GitHub Actions workflows that check out the
instance repo directly
(`llm.py`, `drift.py`, `currency.py`, `merge.py`, `extraction.py`, `skills.py`,
`bootstrap.py`, `diagrams.py`,
`diagram_check.py`, `tooling_currency.py`, and the `parsers/` package) SHALL NOT
be written to the child
repo — they have no role in local Phase 2/3 work and bootstrap.py's own comment
already documents this
CI-only split.

Because the vendored subset and the instance repo's full package share the same
`panopticon` package
name, any CI workflow step that checks out both the child repo (as its working
directory) and the
instance repo (added to `PYTHONPATH`) in the same job SHALL guarantee that
CI-only modules resolve from
the instance repo, not from the child repo's vendored subset. The workflow MUST
NOT rely on `PYTHONPATH`
ordering alone to win this resolution, since `python3 -m`/`-c` prepend the
current working directory to
`sys.path` ahead of `PYTHONPATH` entries.

#### Scenario: Local tooling is usable immediately after bootstrap

- **GIVEN** a freshly bootstrapped child repo that has never had the
  `panopticon` package locally before
- **WHEN** the user's agent follows the `panopticon-doc-generation` skill's
  instructions to run
  `python3 -m panopticon.docs render ...`
- **THEN** the command runs successfully without the user cloning the instance
  repo or configuring
  `PYTHONPATH`

#### Scenario: The sync script is usable immediately after bootstrap

- **GIVEN** a freshly bootstrapped child repo
- **WHEN** the user runs `python3 -m panopticon.sync --check-updates`
- **THEN** the command runs successfully with no instance repo clone or
  `PYTHONPATH` configuration

#### Scenario: The org-diagram link script is usable immediately after bootstrap and initialization

- **GIVEN** a freshly bootstrapped and initialized child repo (so
  `panopticon/config.json` exists with
  `instance`, `instance_default_branch`, and `repo` populated)
- **WHEN** the user runs `python3 -m panopticon.org_diagram_link`
- **THEN** the command runs successfully with no instance repo clone, no
  `PYTHONPATH` configuration, and
  no network call

#### Scenario: CI-only modules are excluded

- **WHEN** the bootstrap script vendors the local-tooling subset
- **THEN** the child repo's `panopticon/` directory contains `__init__.py`,
  `config.py`, `docs.py`,
  `index.py`, `init_repo.py`, `sync.py`, and `org_diagram_link.py`, and none of
  `llm.py`, `drift.py`,
  `currency.py`, `merge.py`, `extraction.py`, `skills.py`, `bootstrap.py`,
  `diagrams.py`,
  `diagram_check.py`, `tooling_currency.py`, or `parsers/`

#### Scenario: Re-run refreshes vendored modules in place

- **WHEN** the bootstrap script runs again on a repo that already has the
  vendored `panopticon/` modules
- **THEN** each of the seven files is overwritten in place with the instance
  repo's current content, and
  no duplicate files are created

#### Scenario: CI resolves instance-only modules despite child vendoring

- **GIVEN** a child repo whose vendored `panopticon/` directory contains only
  the local-tooling subset,
  checked out alongside the instance repo in the same CI job with `PYTHONPATH`
  pointing at the instance
  repo
- **WHEN** a workflow step runs `python3 -m panopticon.drift` (or any other
  CI-only module)
- **THEN** the instance repo's copy of the module runs, and the command MUST NOT
  fail with "No module
  named panopticon.&lt;module&gt;" due to the child repo's partial subset shadowing it
