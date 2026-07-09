## ADDED Requirements

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
4. Download the three caller workflow files from the instance repo and write them to the child repo's
   `.github/workflows/`, creating the directory if absent.
5. Verify org-level CI prerequisites (secrets and variables) and report any missing items — report-only,
   never blocking.
6. Output the exact prompts the user shall give their AI agent to complete the AI-dependent initialization
   steps (see "Agent prompts output").

The bootstrap script SHALL NOT write `panopticon/config.json`. The config file is the last artifact
created, by the finalization step after the agent has completed its work.

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
  the three Panopticon caller workflows, and the terminal prints the agent prompts — without creating
  `panopticon/config.json`

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

### Requirement: Agent prompts output

The bootstrap script SHALL print the exact prompts the user should follow, in order, after completing
all deterministic steps:

1. The literal slash-command invocation for `panopticon-doc-generation` (e.g. `/panopticon-doc-generation`)
   — not a description of what the skill does.
2. The literal slash-command invocations for `panopticon-interface-naming` and
   `panopticon-interface-extraction`, run in sequence.
3. The verbatim shell command to run the finalization step (no user substitution required — the instance
   slug SHALL be interpolated by the bootstrap script before printing).

Each prompt SHALL be the literal text the user pastes into their agent or shell — never a description of
what to ask. A description alongside is acceptable; it SHALL NOT replace the literal invocation.

No prompt text or accompanying prose SHALL assert a single hardcoded skill location (e.g. state or imply
that skills are only ever at `.agents/skills/`) as if it always applies, since the skills location
selection step lets the user pick a different directory. Prompts SHALL refer to invoking skills by their
slash command (which works regardless of which directory the user's agent reads them from) rather than
by claiming a specific path.

The bootstrap script output is the **sole source of truth** for these prompts. Static documentation
(setup guides, READMEs) describing Phase 2 initialization SHALL NOT enumerate the individual prompts —
it SHALL instruct the user to run the bootstrap script and follow its output. Duplicating prompts in
static docs creates drift whenever the prompts change. The same rule about not hardcoding a single skill
location applies to static documentation: any doc, setup guide, or README passage that mentions where
skills live SHALL be written so it stays accurate no matter which location the reader chose.

#### Scenario: Prompts are printed after all deterministic work

- **WHEN** the bootstrap script has successfully installed skills at the chosen location and wired
  workflows
- **THEN** it prints numbered prompts, each containing the literal slash command or shell command to
  paste, and exits with code 0

#### Scenario: Doc-generation prompt contains the slash command, not a description

- **WHEN** the bootstrap script prints the doc-generation prompt
- **THEN** the output contains the text `/panopticon-doc-generation` as a standalone pasteable line, not
  only prose such as "use the panopticon-doc-generation skill"

#### Scenario: Prompt prose does not hardcode a single skill location

- **WHEN** the bootstrap script prints its numbered prompts
- **THEN** no prompt or its accompanying description asserts that skills are only ever at
  `.agents/skills/`; prompts reference the slash command instead

#### Scenario: Setup guide does not enumerate prompts

- **WHEN** a reader follows the setup guide's Phase 2 instructions
- **THEN** they are directed to run the bootstrap script and follow what it prints — the guide does not
  list the individual slash commands

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
exactly the modules that Phase 2 skills and the Phase 3 finalization command invoke directly
(`__init__.py`, `config.py`, `docs.py`, `index.py`, `init_repo.py`) — from the instance repo and write
them to the child repo's `panopticon/` directory, creating it if absent, so `python3 -m panopticon.docs`
and `python3 -m panopticon.init_repo` are runnable immediately after Phase 1 with no manual setup: no
cloning the instance repo, no `PYTHONPATH` configuration, no other local Python environment step.

Modules used only by the reusable GitHub Actions workflows that check out the instance repo directly
(`llm.py`, `drift.py`, `currency.py`, `merge.py`, `extraction.py`, `skills.py`, `bootstrap.py`, and the
`parsers/` package) SHALL NOT be written to the child repo — they have no role in local Phase 2/3 work
and bootstrap.py's own comment already documents this CI-only split.

#### Scenario: Local tooling is usable immediately after bootstrap

- **GIVEN** a freshly bootstrapped child repo that has never had the `panopticon` package locally before
- **WHEN** the user's agent follows the `panopticon-doc-generation` skill's instructions to run
  `python3 -m panopticon.docs render ...`
- **THEN** the command runs successfully without the user cloning the instance repo or configuring
  `PYTHONPATH`

#### Scenario: CI-only modules are excluded

- **WHEN** the bootstrap script vendors the local-tooling subset
- **THEN** the child repo's `panopticon/` directory contains `__init__.py`, `config.py`, `docs.py`,
  `index.py`, and `init_repo.py`, and none of `llm.py`, `drift.py`, `currency.py`, `merge.py`,
  `extraction.py`, `skills.py`, `bootstrap.py`, or `parsers/`

#### Scenario: Re-run refreshes vendored modules in place

- **WHEN** the bootstrap script runs again on a repo that already has the vendored `panopticon/` modules
- **THEN** each of the five files is overwritten in place with the instance repo's current content, and
  no duplicate files are created

## MODIFIED Requirements

### Requirement: Agent-driven initialization

Repo initialization SHALL follow a three-phase sequence:

**Phase 1 — Bootstrap (deterministic, no AI):** the bootstrap installer script installs skills, vendors
the local-tooling subset of the `panopticon` Python package, and wires caller workflows in the child
repo, then outputs guided agent prompts. No `PANOPTICON_LLM_*` or local instance clone is required.

**Phase 2 — Agent (AI-driven):** the user's preferred AI agent follows the installed skills — using the
prompts output by the bootstrap script — to generate the four-layer documentation and build the local
interface index (`panopticon/index.json`). No `PANOPTICON_LLM_*` configuration is required locally;
the agent uses its own harness.

**Phase 3 — Finalization (deterministic):** the finalization step validates that the agent-produced docs
and index meet requirements (all four layers present and following their templates; schema-valid index)
and writes `panopticon/config.json` — the initialization flag — only after that validation passes.
`panopticon/config.json` SHALL be the last artifact created during initialization.

#### Scenario: Successful initialization

- **GIVEN** the bootstrap script has installed skills and workflows and printed agent prompts
- **WHEN** the agent has generated docs and index and the finalization step runs
- **THEN** `panopticon/config.json` is written as the final artifact, and the repo is fully initialized

#### Scenario: Agent output incomplete at finalization

- **WHEN** the finalization step runs before the agent has produced all four documentation layers
- **THEN** no config file is written and the tooling reports exactly which requirements are unmet

### Requirement: Initialization finalization

A finalization command, distinct from the bootstrap script, SHALL validate the agent-produced
documentation and index and write `panopticon/config.json` only when validation passes. It SHALL read
the documentation location from the child repo (adopting an existing docs folder or using the default
`docs/`), record it in the config, and verify org-level CI prerequisites (report-only). The finalization
step SHALL be idempotent: re-running it updates the config in place.

#### Scenario: Validation passes

- **WHEN** all four documentation layers are present and the local index is schema-valid
- **THEN** `panopticon/config.json` is written with `repo`, `instance`, `workflow_ref`, and
  `docs_location` fields

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

Auto-resolution in case 2 is safe because instance repos created via "Use this template" contain only
files that originated from the template; instance-specific files (`panopticon.config.json`, org skills)
do not exist in the template and are therefore never overridden.

#### Scenario: First-time sync after "Use this template"

- **GIVEN** an instance repo created via GitHub's "Use this template" (no shared git history with the template)
- **WHEN** the sync workflow runs
- **THEN** it detects the missing common ancestor, merges with `-X theirs`, and pushes without error

#### Scenario: Routine sync with common ancestor

- **GIVEN** an instance repo that has previously synced with the template (common ancestor exists)
- **WHEN** the sync workflow runs
- **THEN** it merges normally; any genuine divergence surfaces as a conflict with local-resolution instructions

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
