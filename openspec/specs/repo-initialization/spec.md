### Requirement: Bootstrap installer script

The template repo SHALL include a Python bootstrap script that can be run directly from a child repo
without cloning the instance repo locally, invoked via:

```
curl -fsSL https://raw.githubusercontent.com/<instance>/main/install.py | python3
```

or equivalently by downloading and running it. The script SHALL read the instance org/repo slug from the
`PANOPTICON_INSTANCE` environment variable, falling back to an interactive prompt when the variable is not
set and stdin is a terminal. Using only Python stdlib and the GitHub API (no additional dependencies), the
script SHALL:

1. Determine the child repo's skills location (see "Skills location selection") — this SHALL happen
   before any skill files are downloaded.
2. Download only skills whose directory name begins with `panopticon-` from the instance repo's
   `.agents/skills/` directory and write them to the chosen skills location in the child repo, creating
   the directory if absent. Skills at other name prefixes (org-internal skills, tooling skills, etc.)
   SHALL NOT be written to the child repo.
3. Download the local-tooling subset of the `panopticon` Python package into the child repo's
   `panopticon/` directory (see "Local tooling package vendored into child repo").
4. Download the getting-started guide from the instance repo and write it to the child repo's root as
   `PANOPTICON.md` (see "Getting-started guide vendored into child repo").
5. Download the three caller workflow files from the instance repo and write them to the child repo's
   `.github/workflows/`, creating the directory if absent.
6. If `panopticon/config.json` already exists (the repo was already initialized), re-resolve and
   update its `instance_default_branch` field in place (see "Bootstrap script refreshes
   instance_default_branch on rerun") — every other field is left untouched.
7. Verify org-level CI prerequisites (secrets and variables) and report any missing items — report-only,
   never blocking.
8. Output the exact prompts the user shall give their AI agent to complete the AI-dependent initialization
   steps (see "Agent prompts output"), and the sync-workflow reference (see "Bootstrap output references
   the sync workflow and getting-started guide").

The bootstrap script SHALL NOT *create* `panopticon/config.json` — that remains the last artifact
created, by the finalization step, only after the agent has completed its work and validation
passes. Step 6 above is a narrow, explicit exception covering only an update to one field of an
*already-existing* config file on rerun (see "Bootstrap script refreshes instance_default_branch on
rerun"); it does not change when or how the file is first created.

#### Self-bootstrapping when piped via curl

When `install.py` is piped from the instance repo via `curl | python3`, it runs outside the instance repo
directory and cannot import the `panopticon` package locally. The script SHALL detect this condition
(import failure at startup) and self-bootstrap by downloading `panopticon/__init__.py` and
`panopticon/bootstrap.py` from the instance repo via the GitHub API, installing them into `sys.modules`
in-process, then continuing with the normal import flow — without requiring any local clone of the
instance repo.

Token discovery for GitHub API calls SHALL follow the same precedence used by bootstrap.py: `GH_TOKEN`
env var, then `GITHUB_TOKEN` env var, then `gh auth token` if the `gh` CLI is available. When no token is
found the API call is made unauthenticated (suitable for public instance repos; private repos will receive
a 404 and the script SHALL exit with a clear error).

#### Scenario: Only panopticon-prefixed skills are installed

- **GIVEN** the instance repo's `.agents/skills/` contains both `panopticon-doc-generation/` and
  `openspec-apply-change/` (an org-internal skill), and the chosen skills location is `.agents/skills/`
  (the default)
- **WHEN** the bootstrap script runs
- **THEN** `.agents/skills/panopticon-doc-generation/` is written to the child repo and
  `.agents/skills/openspec-apply-change/` is not

#### Scenario: First run in an uninitialised repo

- **WHEN** the bootstrap script runs in a child repo with `PANOPTICON_INSTANCE=acme/panopticon-instance`
  set (or entered at the prompt), and the skills location prompt is accepted at its `.agents/skills/`
  default
- **THEN** the child repo's `.agents/skills/` contains the instance skills, `.github/workflows/` contains
  the three Panopticon caller workflows, the repo root contains `PANOPTICON.md`, and the terminal prints
  the `/panopticon-init` prompt — without creating `panopticon/config.json`

#### Scenario: Piped curl execution with panopticon package unavailable

- **GIVEN** the user runs `curl -fsSL https://raw.githubusercontent.com/<instance>/main/install.py | python3`
  from a child repo that does not contain the `panopticon` package
- **WHEN** the initial import of `panopticon.bootstrap` fails with `ModuleNotFoundError`
- **THEN** the script downloads `panopticon/__init__.py` and `panopticon/bootstrap.py` from the instance
  repo, installs them in-process, and proceeds identically to a local run with no error surfaced to the
  user

#### Scenario: Piped curl execution with PANOPTICON_INSTANCE unset

- **GIVEN** the user pipes `install.py` via curl without setting `PANOPTICON_INSTANCE`
- **WHEN** stdin is not a terminal (no interactive prompt possible)
- **THEN** the script exits with a non-zero code and a message that names the missing env var and shows
  the correct export-and-pipe command

#### Scenario: Instance slug not configured in interactive mode

- **WHEN** the bootstrap script runs with no `PANOPTICON_INSTANCE` env var and stdin is a terminal
- **THEN** the script prompts for the slug and proceeds using the entered value, identical to supplying
  the env var

#### Scenario: Re-run on an already-bootstrapped repo

- **WHEN** the bootstrap script is run again on a repo whose skills and workflows are already installed
- **THEN** all files are updated in place and nothing is duplicated

### Requirement: Download progress reporting

While downloading skills, vendoring local-tooling modules, and writing caller workflows, the bootstrap
script SHALL print one progress line per file as it completes, showing the file's position and the total
count for that step (e.g. `  [3/7] panopticon-doc-generation/SKILL.md`), before that step's existing
summary line. This SHALL apply to each of the three download steps independently. A user watching the
terminal SHALL be able to see how many files remain in the step currently running and confirm the script
is making progress rather than stalled, even when individual network fetches are slow.

#### Scenario: Skills download reports per-file progress

- **GIVEN** the instance repo has 5 `panopticon-*` skill files to download
- **WHEN** the bootstrap script downloads them
- **THEN** it prints a `[1/5]` through `[5/5]` progress line, one per file, before the "skill file(s)
  installed" summary line

#### Scenario: Local tooling vendoring reports per-file progress

- **GIVEN** the local-tooling subset has 5 modules to vendor
- **WHEN** the bootstrap script downloads them
- **THEN** it prints a `[1/5]` through `[5/5]` progress line, one per module, before the "module(s)
  installed" summary line

#### Scenario: Workflow wiring reports per-file progress

- **GIVEN** there are 3 caller workflow files to write
- **WHEN** the bootstrap script wires them
- **THEN** it prints a `[1/3]` through `[3/3]` progress line, one per workflow, before the "workflow(s)
  written" summary line

### Requirement: GitHub API request resilience

The bootstrap script's GitHub API calls (`_api_get`, used by skill downloads, local-tooling vendoring,
workflow wiring, org config fetch, and the org-prerequisites check) SHALL retry transient failures — `429`
and `5xx` responses, and connection-level errors — with exponential backoff before giving up, mirroring
the retry pattern already used by the LLM HTTP client (`panopticon/llm.py`'s `HTTPClient`: up to 3
attempts, backing off `2 ** (attempt - 1)` seconds between attempts). Non-transient errors (`401`, `403`,
`404`) SHALL fail immediately without retrying, since retrying an unauthenticated or missing-resource
request cannot change the outcome. Once retries are exhausted, the script SHALL fail with the same error
detail already shown today (status code and response body), so failures are never silent.

This matters because a full bootstrap run makes many (20+) sequential GitHub API calls — one per skill
file, one per vendored module, one per workflow file — often unauthenticated (see "Bootstrap installer
script"'s token-discovery fallback), which makes transient rate-limit and gateway errors from that
request volume a real, recurring failure mode rather than a rare fluke.

#### Scenario: Transient error is retried and succeeds

- **GIVEN** a GitHub API call returns a `502` on its first attempt and succeeds on its second
- **WHEN** the bootstrap script makes that call
- **THEN** the script retries after a backoff delay and completes the download without surfacing an
  error to the user

#### Scenario: Retries exhausted

- **GIVEN** a GitHub API call returns `503` on all 3 attempts
- **WHEN** the bootstrap script makes that call
- **THEN** it fails with the same status-code-and-body error message format used today, only after
  exhausting its retry budget — not on the first failure

#### Scenario: Non-transient error fails immediately

- **GIVEN** a GitHub API call returns `404` (e.g. the instance repo is private and no token was found)
- **WHEN** the bootstrap script makes that call
- **THEN** it fails immediately with no retry attempts, since a `404` cannot be resolved by retrying

### Requirement: Agent prompts output

The bootstrap script SHALL print exactly one prompt after completing all deterministic steps: the
literal slash-command invocation `/panopticon-init` (see "Orchestrating init skill"), which sequences
documentation generation, interface index building, and finalization on the user's behalf.

The prompt SHALL be the literal text the user pastes into their agent — never a description of what to
ask. A description alongside is acceptable; it SHALL NOT replace the literal invocation.

No prompt text or accompanying prose SHALL assert a single hardcoded skill location (e.g. state or imply
that skills are only ever at `.agents/skills/`) as if it always applies, since the skills location
selection step lets the user pick a different directory. Prompt text SHALL refer to invoking skills by
their slash command (which works regardless of which directory the user's agent reads them from) rather
than by claiming a specific path.

The bootstrap script output is the **sole source of truth** for this prompt. Static documentation (setup
guides, READMEs) describing Phase 2 initialization SHALL NOT restate or paraphrase the prompt — it SHALL
instruct the user to run the bootstrap script and follow its output. Duplicating the prompt in static
docs creates drift whenever it changes. The same rule about not hardcoding a single skill location
applies to static documentation: any doc, setup guide, or README passage that mentions where skills live
SHALL be written so it stays accurate no matter which location the reader chose.

#### Scenario: Prompt is printed after all deterministic work

- **WHEN** the bootstrap script has successfully installed skills at the chosen location, vendored local
  tooling, and wired workflows
- **THEN** it prints the `/panopticon-init` prompt as a standalone pasteable line and exits with code 0

#### Scenario: Prompt contains the slash command, not a description

- **WHEN** the bootstrap script prints its prompt
- **THEN** the output contains the text `/panopticon-init` as a standalone pasteable line, not only
  prose such as "use the panopticon-init skill"

#### Scenario: Prompt prose does not hardcode a single skill location

- **WHEN** the bootstrap script prints its prompt
- **THEN** no accompanying description asserts that skills are only ever at `.agents/skills/`; the prompt
  references the slash command instead

#### Scenario: Setup guide does not enumerate prompts

- **WHEN** a reader follows the setup guide's Phase 2 instructions
- **THEN** they are directed to run the bootstrap script and follow what it prints — the guide does not
  restate the prompt text

### Requirement: Default workflow ref requires no manual instance setup

The bootstrap script SHALL wire child caller workflows to the instance repo's default branch when the
instance's `panopticon.config.json` does not specify `workflow_ref` (including when the instance repo has
no config file yet) — rather than to a git tag. A child repo SHALL be initializable against a freshly
created instance repo with no manual tagging step. Org owners MAY still opt into pinning caller workflows
to a specific tag or branch by setting `workflow_ref` in `panopticon.config.json`. Automated tag-based
release versioning of the instance repo is out of scope for this requirement and is deferred to a future
change.

#### Scenario: Fresh instance repo with no org config and no tags

- **GIVEN** the instance repo has no `panopticon.config.json` and no git tags
- **WHEN** a child repo runs the bootstrap script against that instance
- **THEN** the caller workflows it writes reference the instance repo's default branch, and
  initialization completes without any git tag needing to exist on the instance repo

#### Scenario: Org owner opts into a pinned ref

- **GIVEN** the instance repo's `panopticon.config.json` sets `workflow_ref` to `v1`
- **WHEN** a child repo runs the bootstrap script against that instance
- **THEN** the caller workflows it writes reference `v1` exactly as configured

### Requirement: Template repo ships no pinned workflow_ref

The template repo's own root `panopticon.config.json` SHALL NOT set `workflow_ref`. The template repo has
no release-tagging process (automated tag-based release versioning is out of scope — see "Default
workflow ref requires no manual instance setup"), so a `workflow_ref` committed there could never
correspond to a real tag. Because GitHub's "Use this template" copies the template's root files verbatim
into every new instance repo, a pinned value committed here would silently apply to every instance from
its very first bootstrap — not an opt-in the org owner chose, but an inherited default that breaks caller
workflow resolution (`uses: .../<workflow>@<ref>` resolves to nothing) until someone notices and either
removes it or creates a matching tag. This SHALL be true regardless of whether the value happens to look
plausible (a short tag-like string is not evidence a corresponding git ref exists).

#### Scenario: Template's root config has no workflow_ref key

- **GIVEN** the template repo's root `panopticon.config.json`
- **WHEN** it is read
- **THEN** it does not contain a `workflow_ref` key, so instances created from the template inherit the
  default-branch fallback rather than a pinned ref with no corresponding tag

### Requirement: Recorded workflow_ref matches the wired caller workflows

The finalization step SHALL derive the `workflow_ref` value it writes to `panopticon/config.json` from
the ref actually present in the child repo's already-wired caller workflow
(`.github/workflows/panopticon-pr.yml`'s `uses: owner/repo/.github/workflows/...@ref` line) rather than
from a hardcoded or independently-defaulted value. This SHALL hold regardless of whether that ref is the
instance repo's default branch (the common case — see "Default workflow ref requires no manual instance
setup") or an org-configured pinned tag/branch, so the recorded value can never silently diverge from what
the wired workflows actually reference. Neither the finalization step's own default nor any fallback
constant it uses internally SHALL be a hardcoded ref (e.g. `v1`) unrelated to what was actually wired — a
hardcoded fallback used when derivation is genuinely impossible (e.g. the caller workflow file is missing)
MAY fall back to the child repo's checked-out branch, but SHALL NOT silently imply a git tag exists.

#### Scenario: Recorded workflow_ref reflects the default-branch fallback

- **GIVEN** the bootstrap script wired `.github/workflows/panopticon-pr.yml` with
  `uses: acme/panopticon-instance/.github/workflows/panopticon-pr.yml@main` (the instance repo's default
  branch, because the org has not configured `workflow_ref`)
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `workflow_ref` field is `main`, not `v1` or any other hardcoded value

#### Scenario: Recorded workflow_ref reflects an org-pinned ref

- **GIVEN** the bootstrap script wired `.github/workflows/panopticon-pr.yml` with
  `uses: acme/panopticon-instance/.github/workflows/panopticon-pr.yml@v2` (the org's configured
  `workflow_ref`)
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `workflow_ref` field is `v2`, matching the ref the workflows were actually wired to

### Requirement: Recorded instance_default_branch is resolved deterministically, never guessed

`instance_default_branch` SHALL be resolved via the same GitHub API token/transport mechanism the
bootstrap script already uses for every other instance-repo request (`GH_TOKEN`/`GITHUB_TOKEN`
environment variables, falling back to `gh auth token` only to extract a token — never a direct `gh
api` subprocess call, which depends on the separate, narrower precondition of `gh auth login` having
been run interactively, and can fail even when the token-based mechanism the rest of bootstrap
already relies on works fine). Resolution SHALL NOT hardcode `"main"`, derive the value from
`workflow_ref`, or otherwise guess it. `workflow_ref` MAY reference an org-pinned tag or branch
chosen independently of the instance repo's actual default branch (see "Default workflow ref
requires no manual instance setup"), so conflating the two would silently produce a wrong value for
anything built from `instance_default_branch` (the tooling-currency capability's org-diagram link
script). This mirrors "Recorded workflow_ref matches the wired caller workflows"'s never-guess
discipline, applied to this second, independently-resolved field on the same config file.

Both the bootstrap script (see "Bootstrap script refreshes instance_default_branch on rerun") and
the finalization step use this same resolution logic — sharing the mechanism, not the code path,
since bootstrap.py and init_repo.py cannot import from each other (repo-initialization's existing
CI/local module boundary: init_repo.py is vendored into child repos and cannot import bootstrap.py,
which is CI-only and never vendored).

#### Scenario: Instance's default branch is recorded as-is

- **GIVEN** the instance repo's actual default branch is `main`, and `GH_TOKEN` or `GITHUB_TOKEN` is
  set (or `gh auth token` yields a valid token)
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `instance_default_branch` field is `main`

#### Scenario: Non-standard default branch name is recorded, not overridden

- **GIVEN** the instance repo's actual default branch is `trunk`
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `instance_default_branch` field is `trunk`, not `main`

#### Scenario: workflow_ref and instance_default_branch are resolved independently

- **GIVEN** the org has pinned `workflow_ref` to `v2` in `panopticon.config.json`, and the instance
  repo's actual default branch is `main`
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** `workflow_ref` is `v2` and `instance_default_branch` is `main` — the two fields are never
  conflated or derived from one another

#### Scenario: A working GH_TOKEN resolves the branch even when `gh auth login` was never run

- **GIVEN** `GH_TOKEN` is set to a valid token, and the `gh` CLI is installed but has never had `gh
  auth login` run (so `gh api ...` would fail with an authentication error if called directly)
- **WHEN** the finalization step (or the bootstrap script, on a rerun of an already-initialized
  repo) resolves `instance_default_branch`
- **THEN** resolution succeeds, using `GH_TOKEN` directly rather than depending on `gh`'s own
  separate credential store

### Requirement: Bootstrap script refreshes instance_default_branch on rerun

The bootstrap script SHALL, on an already-initialized repo (one whose `panopticon/config.json`
already exists), re-resolve `instance_default_branch` (same mechanism and never-guess
discipline as "Recorded instance_default_branch is resolved deterministically, never guessed") and
update just that field in `panopticon/config.json` in place, leaving every other field untouched.
This is a narrow, explicit exception to "Bootstrap installer script"'s general rule that the
bootstrap script SHALL NOT write `panopticon/config.json`: that rule protects the file's *creation*
(gated on the finalization step's validation passing, so the file's existence is a trustworthy signal
of "initialization complete") — it was never a statement that the file can never be touched again.
Re-running the bootstrap script is a low-friction, frequently-repeated operation (`PANOPTICON.md`
itself says "Re-run install.py to update") — refreshing this one field there, rather than requiring a
full re-run of finalization (which in turn requires re-running the AI agent), is the appropriate
place for this specific fix to land quickly.

The bootstrap script SHALL still never *create* `panopticon/config.json` — this exception applies
only when the file already exists. On a repo's first bootstrap (config not yet created), resolution
happens the first time via the finalization step, as already specified.

#### Scenario: Rerun on an initialized repo updates only instance_default_branch

- **GIVEN** an already-initialized child repo whose `panopticon/config.json` has
  `instance_default_branch: null` or missing (e.g. finalization couldn't resolve it originally)
- **WHEN** the bootstrap script is re-run and can now resolve the instance's default branch
- **THEN** `panopticon/config.json`'s `instance_default_branch` field is updated in place, and every
  other field (`repo`, `instance`, `workflow_ref`, `docs_location`) is unchanged

#### Scenario: First bootstrap on an uninitialized repo does not create panopticon/config.json

- **GIVEN** a child repo with no `panopticon/config.json` yet (never initialized)
- **WHEN** the bootstrap script runs
- **THEN** `panopticon/config.json` is still not created — only the finalization step, after
  validation passes, creates it (see "Bootstrap installer script")

### Requirement: Skills location selection

The bootstrap script SHALL determine a single skills location for the child repo — the one project-level
directory (e.g. `.agents/skills/`, `.claude/skills/`) that installed skills are written to — before
downloading any skill files, and SHALL prompt for it itself rather than deferring to a separate script or
a later manual step.

The default location SHALL be `.agents/skills/`. Before prompting, the script SHALL print, for each tool
listed in `docs/agentskills-support.md`, which of the candidate locations that tool reads skills from, so
the user can see which single location covers the tools they care about. The user then chooses one of the
candidate locations (the union of every location any listed tool reads):

- **Preferred**: an arrow-key selection menu (up/down to move, enter to confirm), defaulting to
  `.agents/skills/` pre-selected.
- **Fallback**: a plain typed prompt (enter a number or path) when arrow-key selection isn't available in
  the current terminal.

Piped `curl | python3` execution SHALL NOT be treated as non-interactive by default: since stdin is
consumed by the piped script content rather than connected to a terminal, the script SHALL open `/dev/tty`
directly to read the prompt response (and print the menu to it), so the installer itself completes the
whole installation — no separate script or second manual step. A `PANOPTICON_SKILLS_LOCATION` environment
variable overrides the prompt entirely for non-interactive/CI use. When neither `/dev/tty` nor a terminal
stdin nor the environment variable is available (true non-interactive execution, e.g. CI with no
controlling terminal), the script SHALL proceed with the `.agents/skills/` default silently, without
blocking.

Re-running the script SHALL be idempotent: if one of the candidate locations already contains installed
Panopticon skills from a prior run, the script SHALL reuse that location without re-prompting, unless
`PANOPTICON_SKILLS_LOCATION` is set to something else.

#### Scenario: Compatibility table printed before prompting

- **WHEN** the bootstrap script is about to prompt for a skills location
- **THEN** it first prints each tool from `docs/agentskills-support.md` alongside the location(s) it reads
  skills from

#### Scenario: Default location used with no interactive input available

- **GIVEN** `PANOPTICON_SKILLS_LOCATION` is unset, stdin is not a terminal, and `/dev/tty` cannot be
  opened
- **WHEN** the bootstrap script runs
- **THEN** it proceeds with `.agents/skills/` without prompting and without failing

#### Scenario: Piped execution still prompts via /dev/tty

- **GIVEN** the user runs `curl -fsSL .../install.py | python3` from an interactive terminal, so stdin is
  a pipe but `/dev/tty` refers to that terminal
- **WHEN** the bootstrap script reaches the skills location step
- **THEN** it opens `/dev/tty` and prompts there, letting the user choose a location in the same run —
  no second script or manual step is required

#### Scenario: Arrow-key selection

- **GIVEN** an interactive terminal (direct run or piped with `/dev/tty` available) that supports raw
  input mode
- **WHEN** the user presses the down arrow once and then enter
- **THEN** the second candidate location in the printed list is chosen

#### Scenario: Typed fallback when arrow-key mode is unavailable

- **GIVEN** a terminal that does not support raw input mode
- **WHEN** the skills location prompt runs
- **THEN** the user can type a number or path to select a location instead of using arrow keys

#### Scenario: Non-default location chosen

- **GIVEN** the user selects `.claude/skills/` at the prompt
- **WHEN** the bootstrap script downloads skills
- **THEN** skills are written to `.claude/skills/` and `.agents/skills/` is never created

#### Scenario: Environment variable override

- **GIVEN** `PANOPTICON_SKILLS_LOCATION=.cursor/skills` is set
- **WHEN** the bootstrap script runs
- **THEN** it writes skills to `.cursor/skills/` without prompting, identical to selecting it
  interactively

#### Scenario: Re-run reuses the previously chosen location

- **GIVEN** a repo was previously bootstrapped with `.claude/skills/` as the chosen location
- **WHEN** the bootstrap script runs again without `PANOPTICON_SKILLS_LOCATION` set
- **THEN** it reuses `.claude/skills/` without re-prompting, and skills there are refreshed in place

### Requirement: Local tooling package vendored into child repo

The bootstrap script SHALL download the local-tooling subset of the `panopticon` Python package —
the modules that Phase 2 skills and the Phase 3 finalization command invoke directly
(`__init__.py`, `config.py`, `docs.py`, `index.py`, `init_repo.py`), plus the local sync script
(tooling-currency capability) that lets an already-initialized repo pull the instance's current
skills and tooling on demand, plus the org-diagram link script (architecture-diagrams capability,
"Org-diagram link script") that prints a resolvable link to this repo's section of the org diagram —
from the instance repo and write them to the child repo's `panopticon/` directory, creating it if
absent, so `python3 -m panopticon.docs`, `python3 -m panopticon.init_repo`,
`python3 -m panopticon.sync`, and `python3 -m panopticon.org_diagram_link` are all runnable
immediately after Phase 1 with no manual setup: no cloning the instance repo, no `PYTHONPATH`
configuration, no other local Python environment step.

Modules used only by the reusable GitHub Actions workflows that check out the instance repo directly
(`llm.py`, `drift.py`, `currency.py`, `merge.py`, `extraction.py`, `skills.py`, `bootstrap.py`, `diagrams.py`,
`diagram_check.py`, `tooling_currency.py`, and the `parsers/` package) SHALL NOT be written to the child
repo — they have no role in local Phase 2/3 work and bootstrap.py's own comment already documents this
CI-only split.

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

#### Scenario: The org-diagram link script is usable immediately after bootstrap and initialization

- **GIVEN** a freshly bootstrapped and initialized child repo (so `panopticon/config.json` exists with
  `instance`, `instance_default_branch`, and `repo` populated)
- **WHEN** the user runs `python3 -m panopticon.org_diagram_link`
- **THEN** the command runs successfully with no instance repo clone, no `PYTHONPATH` configuration, and
  no network call

#### Scenario: CI-only modules are excluded

- **WHEN** the bootstrap script vendors the local-tooling subset
- **THEN** the child repo's `panopticon/` directory contains `__init__.py`, `config.py`, `docs.py`,
  `index.py`, `init_repo.py`, `sync.py`, and `org_diagram_link.py`, and none of `llm.py`, `drift.py`,
  `currency.py`, `merge.py`, `extraction.py`, `skills.py`, `bootstrap.py`, `diagrams.py`,
  `diagram_check.py`, `tooling_currency.py`, or `parsers/`

#### Scenario: Re-run refreshes vendored modules in place

- **WHEN** the bootstrap script runs again on a repo that already has the vendored `panopticon/` modules
- **THEN** each of the seven files is overwritten in place with the instance repo's current content, and
  no duplicate files are created

#### Scenario: CI resolves instance-only modules despite child vendoring

- **GIVEN** a child repo whose vendored `panopticon/` directory contains only the local-tooling subset,
  checked out alongside the instance repo in the same CI job with `PYTHONPATH` pointing at the instance
  repo
- **WHEN** a workflow step runs `python3 -m panopticon.drift` (or any other CI-only module)
- **THEN** the instance repo's copy of the module runs, and the command MUST NOT fail with "No module
  named panopticon.<module>" due to the child repo's partial subset shadowing it

### Requirement: Getting-started guide vendored into child repo

The bootstrap script SHALL download a single, concise getting-started guide from the instance repo and
write it to the child repo's root as `PANOPTICON.md`, so a maintainer opening the repo sees it
immediately without navigating into `docs/` or `.agents/skills/`. The guide's content SHALL be static and
template-authored — downloaded verbatim, identical across every child repo of a given instance, never
per-repo generated or agent-written — mirroring how skills and vendored tooling modules are downloaded
as-is rather than templated. Re-running the bootstrap script SHALL overwrite `PANOPTICON.md` in place,
the same idempotent-overwrite trust model already used for skills and vendored tooling.

The guide SHALL, at minimum, describe: (1) the three repo roles (template, instance, child) and the
pull-request/merge lifecycle in brief, so a new maintainer has the same orientation the setup guide gives
an org owner; (2) where architecture diagrams live — this repo's own `## Architecture diagram` section
in its `architecture.md`, and the org-wide diagram at the instance repo's `docs/architecture.md`; and
(3) exactly how to keep this repo's skills and vendored tooling current — the literal
`python3 -m panopticon.sync` and `python3 -m panopticon.sync --check-updates` commands (tooling-currency
capability).

#### Scenario: Getting-started guide is downloaded on first bootstrap

- **WHEN** the bootstrap script runs in a child repo for the first time
- **THEN** the child repo's root contains `PANOPTICON.md`, downloaded from the instance repo

#### Scenario: Getting-started guide is refreshed on re-run

- **WHEN** the bootstrap script runs again on an already-bootstrapped repo
- **THEN** `PANOPTICON.md` is overwritten in place with the instance repo's current content, and no
  duplicate file is created

#### Scenario: Guide documents the sync command

- **WHEN** a maintainer reads `PANOPTICON.md`
- **THEN** it contains the literal command `python3 -m panopticon.sync` and explains that it pulls the
  instance repo's current skills and vendored tooling into this repo

#### Scenario: Guide points to both diagram locations

- **WHEN** a maintainer reads `PANOPTICON.md` looking for architecture diagrams
- **THEN** it names both this repo's own `## Architecture diagram` section and the instance repo's
  org-wide `docs/architecture.md`

### Requirement: Bootstrap output references the sync workflow and getting-started guide

The bootstrap script's printed output SHALL, on every run — first bootstrap and idempotent re-run
alike — explicitly name `PANOPTICON.md`'s location and the literal `python3 -m panopticon.sync` command
(including its `--check-updates` dry-run flag), so a maintainer discovers the sync workflow directly from
the terminal output without first having to know `PANOPTICON.md` exists or read source code. This output
is distinct from the `/panopticon-init` agent prompt (see "Agent prompts output") — it SHALL be present
regardless of whether that prompt is also printed.

#### Scenario: First run prints the sync command and guide location

- **WHEN** the bootstrap script completes a first-time run
- **THEN** its output contains both `PANOPTICON.md` and the literal text `python3 -m panopticon.sync`

#### Scenario: Re-run also prints the sync command and guide location

- **WHEN** the bootstrap script is run again on an already-bootstrapped repo
- **THEN** its output still contains both `PANOPTICON.md` and `python3 -m panopticon.sync` — this is not
  gated behind "first run only", since a maintainer re-running the script specifically to pick up a
  tooling-currency fix needs to see it every time

### Requirement: Orchestrating init skill

The template repo SHALL include a `panopticon-init` skill (name prefix `panopticon-`, so the existing
skill-download step installs it into the child repo automatically with no bootstrap script changes) that
runs the other Phase 2 skills and the Phase 3 finalization command in the correct dependency order, from
a single invocation, while leaving each underlying skill independently invocable on its own.

The order SHALL be:

1. `panopticon-interface-naming`
2. `panopticon-interface-extraction` — after step 1, since it depends on the naming pass
3. `panopticon-doc-generation` — after steps 1–2, since the interface-docs layer is rendered from the
   local index (`panopticon/index.json`) that those steps build; running doc-generation first has no
   index to render from
4. The finalization command (`python3 -m panopticon.init_repo --instance <instance>`) — the instance
   slug SHALL be self-discovered by reading the `uses:` line already wired into
   `.github/workflows/panopticon-pr.yml`, rather than requiring the user to supply it

`panopticon-init` SHALL maintain a checkpoint log at `panopticon/.init-log.json` recording which of the
four steps have completed. Before starting a step, it SHALL check the log and skip any step already
recorded as complete. It SHALL update the log immediately after each step completes, so an interrupted
run — including one resumed in a new agent session with no memory of the prior one — continues from the
first incomplete step rather than restarting from scratch or skipping ahead into a step whose
prerequisites aren't met. Once all four steps have completed and `panopticon/config.json` has been
written, `panopticon-init` SHALL delete the checkpoint log — a completed initialization has no further
use for it, and it SHALL NOT remain in the repo afterward.

Each of the four skills SHALL remain fully usable on its own, independent of `panopticon-init` and of any
checkpoint log state, for users who want to run a single step directly.

#### Scenario: Fresh run starts at interface naming

- **GIVEN** no checkpoint log exists
- **WHEN** `/panopticon-init` runs
- **THEN** it starts with `panopticon-interface-naming`, then creates the checkpoint log recording that
  step's completion before continuing

#### Scenario: Doc generation runs only after the index exists

- **GIVEN** the checkpoint log shows `panopticon-interface-naming` and `panopticon-interface-extraction`
  complete
- **WHEN** `panopticon-init` continues
- **THEN** it runs `panopticon-doc-generation` next, with a populated local index to render
  `interfaces.md` from

#### Scenario: Resuming after an interrupted session

- **GIVEN** a checkpoint log recording `panopticon-interface-naming` and `panopticon-interface-extraction`
  as complete, from a prior agent session that did not finish
- **WHEN** `/panopticon-init` is invoked again, in a new agent session with no memory of the prior one
- **THEN** it skips the two completed steps and resumes at `panopticon-doc-generation`

#### Scenario: Checkpoint log deleted on successful completion

- **GIVEN** all four steps have completed and `panopticon/config.json` has been written
- **WHEN** `panopticon-init` finishes
- **THEN** `panopticon/.init-log.json` no longer exists in the repo

#### Scenario: Individual skills remain independently invocable

- **WHEN** a user invokes `/panopticon-doc-generation` directly instead of `/panopticon-init`
- **THEN** it runs as its own standalone skill, unaffected by whether a checkpoint log exists

#### Scenario: Finalization instance slug is self-discovered

- **WHEN** `panopticon-init` reaches the finalization step
- **THEN** it determines the instance slug by reading the `uses:` line in
  `.github/workflows/panopticon-pr.yml` rather than asking the user for it

### Requirement: Agent-driven initialization

Repo initialization SHALL follow a three-phase sequence:

**Phase 1 — Bootstrap (deterministic, no AI):** the bootstrap installer script installs skills, vendors
the local-tooling subset of the `panopticon` Python package, and wires caller workflows in the child
repo, then outputs the `/panopticon-init` prompt. No `PANOPTICON_LLM_*` or local instance clone is
required.

**Phase 2 — Agent (AI-driven):** the user's preferred AI agent follows the `panopticon-init` skill
invoked by the bootstrap script's printed prompt, which sequences the interface-naming,
interface-extraction, and doc-generation skills in dependency order (with a resumable checkpoint log) to
build the local interface index (`panopticon/index.json`) and generate the four-layer documentation. No
`PANOPTICON_LLM_*` configuration is required locally; the agent uses its own harness.

**Phase 3 — Finalization (deterministic):** the finalization step validates that the agent-produced docs
and index meet requirements (all four layers present and following their templates; schema-valid index)
and writes `panopticon/config.json` — the initialization flag — only after that validation passes.
`panopticon/config.json` SHALL be the last artifact created during initialization.

#### Scenario: Successful initialization

- **GIVEN** the bootstrap script has installed skills and workflows and printed the `/panopticon-init`
  prompt
- **WHEN** the agent has generated docs and index and the finalization step runs
- **THEN** `panopticon/config.json` is written as the final artifact, and the repo is fully initialized

#### Scenario: Agent output incomplete at finalization

- **WHEN** the finalization step runs before the agent has produced all four documentation layers
- **THEN** no config file is written and the tooling reports exactly which requirements are unmet

### Requirement: Initialization finalization

A finalization command, distinct from the bootstrap script, SHALL validate the agent-produced
documentation and index and write `panopticon/config.json` only when validation passes. It SHALL read
the documentation location from the child repo (adopting an existing docs folder or using the default
`docs/`), record it in the config along with `instance_default_branch` (see "Recorded
instance_default_branch is resolved deterministically, never guessed"), and verify org-level CI
prerequisites (report-only). The finalization step SHALL be idempotent: re-running it updates the config
in place.

#### Scenario: Validation passes

- **WHEN** all four documentation layers are present and the local index is schema-valid
- **THEN** `panopticon/config.json` is written with `repo`, `instance`, `workflow_ref`, `docs_location`,
  and `instance_default_branch` fields

#### Scenario: Re-finalization after a docs update

- **WHEN** the finalization step is run again on an already-initialized repo
- **THEN** `panopticon/config.json` is updated in place and no duplicate files are created

### Requirement: Org-level CI prerequisites

The init tooling SHALL verify that the org-level **secrets** `PANOPTICON_LLM_API_KEY` and
`PANOPTICON_INSTANCE_TOKEN`, and the org-level **variables** `PANOPTICON_LLM_ENDPOINT` and
`PANOPTICON_LLM_MODEL`, are all configured and available to the child repo — they are consumed only by the
shared CI workflows. Child repos MUST NOT require per-repo secret or variable configuration: the caller
workflows a child repo receives are trivial references to the shared workflows. Missing secrets or
variables SHALL NOT block any initialization step.

Verifying org-level secrets and variables requires a GitHub auth token with permission to read org-level
Actions secrets/variables (an admin-scoped token). The presence or absence of such a token determines how
the check behaves:

- **Token available** (resolved via `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`): the tooling SHALL query
  the org's secrets and variables directly via the GitHub API and generate the report automatically,
  listing exactly which required secrets and variables are missing and how to configure each, distinguishing
  whether each missing item is a secret or a variable.
- **No token available**: this SHALL NOT be reported or treated as an error or failure of initialization.
  Instead the tooling SHALL print the manual steps the user can take to perform the verification themselves,
  covering both:
  1. the GitHub web UI path — the org's Settings → Secrets and variables → Actions page (secrets and
     variables have separate tabs) — where the required names can be checked directly, and
  2. the equivalent local `gh` CLI commands (`gh secret list --org <org>` and `gh variable list --org <org>`,
     run after `gh auth login` if not already authenticated) that list the same information.

  The printed steps SHALL name all four required items (`PANOPTICON_LLM_API_KEY`, `PANOPTICON_INSTANCE_TOKEN`,
  `PANOPTICON_LLM_ENDPOINT`, `PANOPTICON_LLM_MODEL`) so the user knows what to look for, since the tooling
  cannot determine on its own which are already configured.

#### Scenario: Missing instance token

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization runs for a repo whose org has not configured `PANOPTICON_INSTANCE_TOKEN`
- **THEN** it reports which org-level secret is missing and how to configure it before workflow wiring is
  considered complete

#### Scenario: Missing endpoint variable

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization runs for a repo whose org has not configured the `PANOPTICON_LLM_ENDPOINT` variable
- **THEN** it reports which org-level variable is missing and how to configure it before workflow wiring is
  considered complete

#### Scenario: Auth token available — automated report generated

- **GIVEN** a GitHub auth token is resolved from `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`
- **WHEN** the org-level prerequisite check runs
- **THEN** it queries the org secrets and variables APIs directly and reports exactly which required items
  are missing — the report contains no mention of a missing or absent token

#### Scenario: No auth token available — manual verification steps printed

- **GIVEN** no GitHub auth token can be resolved from `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`
- **WHEN** the org-level prerequisite check runs
- **THEN** it prints, without reporting an error or failure, the web UI navigation path and the equivalent
  `gh secret list --org` / `gh variable list --org` commands, and lists all four required secret/variable
  names so the user can verify each one manually

### Requirement: Documentation location adoption

When the child repo already has documentation, initialization SHALL adopt that location as the
documentation source. When no documentation exists, the user SHALL be prompted for the desired location,
with `docs/` as the default. The chosen location SHALL be recorded in `panopticon/config.json`.

#### Scenario: Repo with existing docs

- **WHEN** the finalization step runs on a repo with an existing documentation folder
- **THEN** that folder is configured as the doc source

#### Scenario: Repo without docs

- **WHEN** the finalization step runs on a repo with no existing documentation
- **THEN** the user is prompted for the desired location, defaulting to `docs/`

### Requirement: Template update workflow

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

### Requirement: Idempotent re-initialization

Re-running the bootstrap script or the finalization step on an already-initialized repo SHALL update all
artifacts in place without creating duplicates.

#### Scenario: Re-run bootstrap on initialized repo

- **WHEN** the bootstrap script runs again on a repo that already has Panopticon skills, vendored local
  tooling, and workflows
- **THEN** skills (at the previously chosen location), the vendored `panopticon/` modules, and workflows
  are refreshed in place and no duplicates are created

#### Scenario: Re-run finalization on initialized repo

- **WHEN** the finalization step runs again on a repo that already has `panopticon/config.json`
- **THEN** the config is updated in place and no duplicate files are created
