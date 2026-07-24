# Repository Initialization Specification

## Purpose

Define how Panopticon bootstraps, configures, validates, and updates child and
instance repositories.

## Requirements

### Requirement: Bootstrap installer script

The template repo SHALL publish a Python standard-library-only launcher that can
be piped directly into
Python from a stable, organization-neutral public-template URL while the user's
working directory is the
child repo to initialize. The same launcher command SHALL support public and
private instance repositories.

The launcher SHALL resolve the instance org/repo slug from
`PANOPTICON_INSTANCE`, or prompt through the
controlling terminal when the variable is absent and interactive input is
available. It SHALL resolve the
instance ref from `PANOPTICON_INSTANCE_REF` when set; otherwise it SHALL query
the GitHub repository API
for the instance repository's actual default branch rather than assuming a
branch name.

Authentication SHALL be resolved in this order: `GH_TOKEN`, `GITHUB_TOKEN`, then
`gh auth token` when the
GitHub CLI is available. With no resolved token, the launcher SHALL first
attempt anonymous GitHub API
access so public instances require no authentication. When anonymous access
cannot retrieve the instance
and a controlling terminal is available, the launcher SHALL offer a hidden token
prompt and retry with
the entered token. In non-interactive execution it SHALL fail clearly and name
the environment variables
needed to continue.

After resolving access and the ref, the launcher SHALL fetch the selected
instance repository's complete
`install.py` through the GitHub contents API and execute it as the installation
payload in the current
process and child-repository working directory. It SHALL pass through the
existing environment unchanged,
apart from making launcher-resolved universal values available to the payload,
so the instance installer
retains control of organization-specific prompts, parameters, skills locations,
files, and behavior. The
launcher SHALL prevent a fetched payload from recursively re-entering the
launcher dispatch phase.
The launcher SHALL accept the GitHub contents API's whitespace-wrapped base64
representation while still
strictly validating the normalized payload as base64 and UTF-8 before execution.
The template-derived
instance payload SHALL apply the same decoding behavior when it fetches its
default bootstrap modules.

The launcher and its diagnostics SHALL never place a token in a URL or command
argument, echo a token,
include a token or authenticated response body in an error, or persist a
prompted token to disk or Git
credential storage. Hidden token input SHALL not be displayed. A token entered
interactively SHALL exist
only for the lifetime of the launcher process and its instance-installer
payload.

The instance installer remains responsible for the deterministic installation
behavior defined by the
instance, including the template default behavior of selecting a skills
location, downloading only
`panopticon-` skills, vendoring local tooling and the getting-started guide,
writing caller workflows,
refreshing an existing `panopticon/config.json`, reporting CI prerequisites, and
printing agent and sync
instructions. The instance installer SHALL NOT create `panopticon/config.json`;
finalization remains
responsible for its initial creation after validation.

#### Scenario: Public instance uses anonymous access

- **GIVEN** `PANOPTICON_INSTANCE` names a public instance repository and no
  GitHub token is available
- **WHEN** the user pipes the public template launcher into Python
- **THEN** the launcher resolves the default branch, retrieves the instance
  `install.py` anonymously,
  and executes it without asking for authentication

#### Scenario: Private instance uses existing authentication

- **GIVEN** `PANOPTICON_INSTANCE` names a private instance repository and
  `GH_TOKEN`, `GITHUB_TOKEN`, or
  `gh auth token` provides access
- **WHEN** the public template launcher runs
- **THEN** the launcher retrieves and executes the private instance's
  `install.py` without exposing the
  token

#### Scenario: Private instance prompts securely for authentication

- **GIVEN** the instance installer cannot be retrieved anonymously, no existing
  token is available, and
  the launcher has a controlling terminal
- **WHEN** the public template launcher runs
- **THEN** it requests a token using hidden input, retries the GitHub API
  request, and makes the token
  available to the instance payload only for the current process without
  displaying or persisting it

#### Scenario: Missing instance is prompted while launcher input is piped

- **GIVEN** `PANOPTICON_INSTANCE` is unset and the launcher source is arriving
  through piped stdin
- **WHEN** a controlling terminal is available
- **THEN** the launcher prompts for `owner/repo` through the controlling
  terminal and continues without
  consuming installer-source bytes as user input

#### Scenario: Non-interactive inputs are incomplete

- **GIVEN** no controlling terminal is available
- **WHEN** the instance slug or authentication required to retrieve a private
  instance is unavailable
- **THEN** the launcher exits non-zero with instructions naming
  `PANOPTICON_INSTANCE` and the applicable
  token environment variables, without printing secret values

#### Scenario: Explicit instance ref is honored

- **GIVEN** `PANOPTICON_INSTANCE_REF` names a branch, tag, or commit containing
  a customized installer
- **WHEN** the launcher retrieves the instance payload
- **THEN** it fetches `install.py` at that exact ref instead of resolving or
  using the default branch

#### Scenario: GitHub-wrapped base64 payload is decoded

- **GIVEN** the GitHub contents API returns a valid installer or default
  bootstrap module whose base64
  content contains transport whitespace and line wrapping
- **WHEN** the launcher or template-derived instance payload decodes that
  content
- **THEN** it removes the transport whitespace, strictly validates the remaining
  base64 and UTF-8 content,
  and executes the decoded source

#### Scenario: Malformed payload remains rejected

- **GIVEN** the GitHub contents API response declares base64 content but the
  normalized payload is not
  valid base64 or does not decode as UTF-8
- **WHEN** the launcher or template-derived instance payload decodes that
  content
- **THEN** it exits non-zero with a controlled invalid-payload error and does
  not execute the content

#### Scenario: Customized instance installer receives control

- **GIVEN** the selected instance's `install.py` defines organization-specific
  prompts and installation
  behavior
- **WHEN** the launcher executes the fetched payload
- **THEN** the payload runs in the child repository with terminal access and the
  caller's environment,
  including `PANOPTICON_SKILLS_LOCATION` when supplied, without the launcher
  imposing template bootstrap
  steps

#### Scenario: Instance payload does not recursively dispatch

- **GIVEN** the fetched instance installer was forked from a template version
  that recognizes the
  launcher execution marker
- **WHEN** it starts as the selected payload
- **THEN** it performs instance installation rather than fetching and executing
  itself again

#### Scenario: Default template instance behavior remains available

- **GIVEN** an instance has not customized the template's installation payload
- **WHEN** its fetched `install.py` executes
- **THEN** it installs the instance's Panopticon skills, tooling, workflows, and
  guide, prints the agent
  prompt, and does not create `panopticon/config.json`

#### Scenario: Re-run remains idempotent

- **WHEN** the public launcher dispatches the instance installer in an
  already-bootstrapped child repo
- **THEN** the instance installer updates its managed files in place and does
  not duplicate them

### Requirement: Download progress reporting

The bootstrap script SHALL, while downloading skills, vendoring local-tooling
modules, and writing caller
workflows, print one progress line per file as it completes, showing the file's
position and the total
count for that step (e.g. `[3/7] panopticon-doc-generation/SKILL.md`), before
that step's existing
summary line. This SHALL apply to each of the three download steps
independently. A user watching the
terminal SHALL be able to see how many files remain in the step currently
running and confirm the script
is making progress rather than stalled, even when individual network fetches are
slow.

#### Scenario: Skills download reports per-file progress

- **GIVEN** the instance repo has 5 `panopticon-*` skill files to download
- **WHEN** the bootstrap script downloads them
- **THEN** it prints a `[1/5]` through `[5/5]` progress line, one per file,
  before the "skill file(s)
  installed" summary line

#### Scenario: Local tooling vendoring reports per-file progress

- **GIVEN** the local-tooling subset has 5 modules to vendor
- **WHEN** the bootstrap script downloads them
- **THEN** it prints a `[1/5]` through `[5/5]` progress line, one per module,
  before the "module(s)
  installed" summary line

#### Scenario: Workflow wiring reports per-file progress

- **GIVEN** there are 3 caller workflow files to write
- **WHEN** the bootstrap script wires them
- **THEN** it prints a `[1/3]` through `[3/3]` progress line, one per workflow,
  before the "workflow(s)
  written" summary line

### Requirement: GitHub API request resilience

The bootstrap script SHALL retry transient failures from its GitHub API calls
(`_api_get`, used by skill
downloads, local-tooling vendoring, workflow wiring, org config fetch, and the
org-prerequisites check) — `429`
and `5xx` responses, and connection-level errors — with exponential backoff
before giving up, mirroring
the retry pattern already used by the LLM HTTP client (`panopticon/llm.py`'s
`HTTPClient`: up to 3
attempts, backing off `2 ** (attempt - 1)` seconds between attempts).
Non-transient errors (`401`, `403`,
`404`) SHALL fail immediately without retrying, since retrying an
unauthenticated or missing-resource
request cannot change the outcome. Once retries are exhausted, the script SHALL
fail with the same error
detail already shown today (status code and response body), so failures are
never silent.

This matters because a full bootstrap run makes many (20+) sequential GitHub API
calls — one per skill
file, one per vendored module, one per workflow file — often unauthenticated
(see "Bootstrap installer
script"'s token-discovery fallback), which makes transient rate-limit and
gateway errors from that
request volume a real, recurring failure mode rather than a rare fluke.

#### Scenario: Transient error is retried and succeeds

- **GIVEN** a GitHub API call returns a `502` on its first attempt and succeeds
  on its second
- **WHEN** the bootstrap script makes that call
- **THEN** the script retries after a backoff delay and completes the download
  without surfacing an
  error to the user

#### Scenario: Retries exhausted

- **GIVEN** a GitHub API call returns `503` on all 3 attempts
- **WHEN** the bootstrap script makes that call
- **THEN** it fails with the same status-code-and-body error message format used
  today, only after
  exhausting its retry budget — not on the first failure

#### Scenario: Non-transient error fails immediately

- **GIVEN** a GitHub API call returns `404` (e.g. the instance repo is private
  and no token was found)
- **WHEN** the bootstrap script makes that call
- **THEN** it fails immediately with no retry attempts, since a `404` cannot be
  resolved by retrying

### Requirement: Agent prompts output

The bootstrap script SHALL print exactly one prompt after completing all
deterministic steps: the
literal slash-command invocation `/panopticon-init` (see "Orchestrating init
skill"), which sequences
documentation generation, interface index building, and finalization on the
user's behalf.

The prompt SHALL be the literal text the user pastes into their agent — never a
description of what to
ask. A description alongside is acceptable; it SHALL NOT replace the literal
invocation.

No prompt text or accompanying prose SHALL assert a single hardcoded skill
location (e.g. state or imply
that skills are only ever at `.agents/skills/`) as if it always applies, since
the skills location
selection step lets the user pick a different directory. Prompt text SHALL refer
to invoking skills by
their slash command (which works regardless of which directory the user's agent
reads them from) rather
than by claiming a specific path.

The bootstrap script output is the **sole source of truth** for this prompt.
Static documentation (setup
guides, READMEs) describing Phase 2 initialization SHALL NOT restate or
paraphrase the prompt — it SHALL
instruct the user to run the bootstrap script and follow its output. Duplicating
the prompt in static
docs creates drift whenever it changes. The same rule about not hardcoding a
single skill location
applies to static documentation: any doc, setup guide, or README passage that
mentions where skills live
SHALL be written so it stays accurate no matter which location the reader chose.

#### Scenario: Prompt is printed after all deterministic work

- **WHEN** the bootstrap script has successfully installed skills at the chosen
  location, vendored local
  tooling, and wired workflows
- **THEN** it prints the `/panopticon-init` prompt as a standalone pasteable
  line and exits with code 0

#### Scenario: Prompt contains the slash command, not a description

- **WHEN** the bootstrap script prints its prompt
- **THEN** the output contains the text `/panopticon-init` as a standalone
  pasteable line, not only
  prose such as "use the panopticon-init skill"

#### Scenario: Prompt prose does not hardcode a single skill location

- **WHEN** the bootstrap script prints its prompt
- **THEN** no accompanying description asserts that skills are only ever at
  `.agents/skills/`; the prompt
  references the slash command instead

#### Scenario: Setup guide does not enumerate prompts

- **WHEN** a reader follows the setup guide's Phase 2 instructions
- **THEN** they are directed to run the bootstrap script and follow what it
  prints — the guide does not
  restate the prompt text

### Requirement: Default workflow ref requires no manual instance setup

The bootstrap script SHALL wire child caller workflows to the instance repo's
default branch when the
instance's `panopticon.config.json` does not specify `workflow_ref` (including
when the instance repo has
no config file yet) — rather than to a git tag. A child repo SHALL be
initializable against a freshly
created instance repo with no manual tagging step. Org owners MAY still opt into
pinning caller workflows
to a specific tag or branch by setting `workflow_ref` in
`panopticon.config.json`. Automated tag-based
release versioning of the instance repo is out of scope for this requirement and
is deferred to a future
change.

#### Scenario: Fresh instance repo with no org config and no tags

- **GIVEN** the instance repo has no `panopticon.config.json` and no git tags
- **WHEN** a child repo runs the bootstrap script against that instance
- **THEN** the caller workflows it writes reference the instance repo's default
  branch, and
  initialization completes without any git tag needing to exist on the instance
  repo

#### Scenario: Org owner opts into a pinned ref

- **GIVEN** the instance repo's `panopticon.config.json` sets `workflow_ref` to
  `v1`
- **WHEN** a child repo runs the bootstrap script against that instance
- **THEN** the caller workflows it writes reference `v1` exactly as configured

### Requirement: Template repo ships no pinned workflow_ref

The template repo's own root `panopticon.config.json` SHALL NOT set
`workflow_ref`. The template repo has
no release-tagging process (automated tag-based release versioning is out of
scope — see "Default
workflow ref requires no manual instance setup"), so a `workflow_ref` committed
there could never
correspond to a real tag. Because GitHub's "Use this template" copies the
template's root files verbatim
into every new instance repo, a pinned value committed here would silently apply
to every instance from
its very first bootstrap — not an opt-in the org owner chose, but an inherited
default that breaks caller
workflow resolution (`uses: .../<workflow>@<ref>` resolves to nothing) until
someone notices and either
removes it or creates a matching tag. This SHALL be true regardless of whether
the value happens to look
plausible (a short tag-like string is not evidence a corresponding git ref
exists).

#### Scenario: Template's root config has no workflow_ref key

- **GIVEN** the template repo's root `panopticon.config.json`
- **WHEN** it is read
- **THEN** it does not contain a `workflow_ref` key, so instances created from
  the template inherit the
  default-branch fallback rather than a pinned ref with no corresponding tag

### Requirement: Recorded workflow_ref matches the wired caller workflows

The finalization step SHALL derive the `workflow_ref` value it writes to
`panopticon/config.json` from
the ref actually present in the child repo's already-wired caller workflow
(`.github/workflows/panopticon-pr.yml`'s `uses:
owner/repo/.github/workflows/...@ref` line) rather than
from a hardcoded or independently-defaulted value. This SHALL hold regardless of
whether that ref is the
instance repo's default branch (the common case — see "Default workflow ref
requires no manual instance
setup") or an org-configured pinned tag/branch, so the recorded value can never
silently diverge from what
the wired workflows actually reference. Neither the finalization step's own
default nor any fallback
constant it uses internally SHALL be a hardcoded ref (e.g. `v1`) unrelated to
what was actually wired — a
hardcoded fallback used when derivation is genuinely impossible (e.g. the caller
workflow file is missing)
MAY fall back to the child repo's checked-out branch, but SHALL NOT silently
imply a git tag exists.

#### Scenario: Recorded workflow_ref reflects the default-branch fallback

- **GIVEN** the bootstrap script wired `.github/workflows/panopticon-pr.yml`
  with
  `uses: acme/panopticon-instance/.github/workflows/panopticon-pr.yml@main` (the
  instance repo's default
  branch, because the org has not configured `workflow_ref`)
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `workflow_ref` field is `main`, not `v1` or any other hardcoded
  value

#### Scenario: Recorded workflow_ref reflects an org-pinned ref

- **GIVEN** the bootstrap script wired `.github/workflows/panopticon-pr.yml`
  with
  `uses: acme/panopticon-instance/.github/workflows/panopticon-pr.yml@v2` (the
  org's configured
  `workflow_ref`)
- **WHEN** the finalization step runs and writes `panopticon/config.json`
- **THEN** the `workflow_ref` field is `v2`, matching the ref the workflows were
  actually wired to

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

### Requirement: Skills location selection

The bootstrap script SHALL determine a single skills location for the child repo
— the one project-level
directory (e.g. `.agents/skills/`, `.claude/skills/`) that installed skills are
written to — before
downloading any skill files, and SHALL prompt for it itself rather than
deferring to a separate script or
a later manual step.

The default location SHALL be `.agents/skills/`. Before prompting, the script
SHALL print, for each tool
listed in `docs/agentskills-support.md`, which of the candidate locations that
tool reads skills from, so
the user can see which single location covers the tools they care about. The
user then chooses one of the
candidate locations (the union of every location any listed tool reads):

- **Preferred**: an arrow-key selection menu (up/down to move, enter to
  confirm), defaulting to
  `.agents/skills/` pre-selected.
- **Fallback**: a plain typed prompt (enter a number or path) when arrow-key
  selection isn't available in
  the current terminal.

Piped `curl | python3` execution SHALL NOT be treated as non-interactive by
default: since stdin is
consumed by the piped script content rather than connected to a terminal, the
script SHALL open `/dev/tty`
directly to read the prompt response (and print the menu to it), so the
installer itself completes the
whole installation — no separate script or second manual step. A
`PANOPTICON_SKILLS_LOCATION` environment
variable overrides the prompt entirely for non-interactive/CI use. When neither
`/dev/tty` nor a terminal
stdin nor the environment variable is available (true non-interactive execution,
e.g. CI with no
controlling terminal), the script SHALL proceed with the `.agents/skills/`
default silently, without
blocking.

Re-running the script SHALL be idempotent: if one of the candidate locations
already contains installed
Panopticon skills from a prior run, the script SHALL reuse that location without
re-prompting, unless
`PANOPTICON_SKILLS_LOCATION` is set to something else.

#### Scenario: Compatibility table printed before prompting

- **WHEN** the bootstrap script is about to prompt for a skills location
- **THEN** it first prints each tool from `docs/agentskills-support.md`
  alongside the location(s) it reads
  skills from

#### Scenario: Default location used with no interactive input available

- **GIVEN** `PANOPTICON_SKILLS_LOCATION` is unset, stdin is not a terminal, and
  `/dev/tty` cannot be
  opened
- **WHEN** the bootstrap script runs
- **THEN** it proceeds with `.agents/skills/` without prompting and without
  failing

#### Scenario: Piped execution still prompts via /dev/tty

- **GIVEN** the user runs `curl -fsSL .../install.py | python3` from an
  interactive terminal, so stdin is
  a pipe but `/dev/tty` refers to that terminal
- **WHEN** the bootstrap script reaches the skills location step
- **THEN** it opens `/dev/tty` and prompts there, letting the user choose a
  location in the same run —
  no second script or manual step is required

#### Scenario: Arrow-key selection

- **GIVEN** an interactive terminal (direct run or piped with `/dev/tty`
  available) that supports raw
  input mode
- **WHEN** the user presses the down arrow once and then enter
- **THEN** the second candidate location in the printed list is chosen

#### Scenario: Typed fallback when arrow-key mode is unavailable

- **GIVEN** a terminal that does not support raw input mode
- **WHEN** the skills location prompt runs
- **THEN** the user can type a number or path to select a location instead of
  using arrow keys

#### Scenario: Non-default location chosen

- **GIVEN** the user selects `.claude/skills/` at the prompt
- **WHEN** the bootstrap script downloads skills
- **THEN** skills are written to `.claude/skills/` and `.agents/skills/` is
  never created

#### Scenario: Environment variable override

- **GIVEN** `PANOPTICON_SKILLS_LOCATION=.cursor/skills` is set
- **WHEN** the bootstrap script runs
- **THEN** it writes skills to `.cursor/skills/` without prompting, identical to
  selecting it
  interactively

#### Scenario: Re-run reuses the previously chosen location

- **GIVEN** a repo was previously bootstrapped with `.claude/skills/` as the
  chosen location
- **WHEN** the bootstrap script runs again without `PANOPTICON_SKILLS_LOCATION`
  set
- **THEN** it reuses `.claude/skills/` without re-prompting, and skills there
  are refreshed in place

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

### Requirement: Vendored tooling's bytecode cache is gitignored

The bootstrap script SHALL, whenever it vendors the local-tooling subset of the
`panopticon` package (see
"Local tooling package vendored into child repo"), also write
`panopticon/.gitignore`
containing `__pycache__/`, so that running the vendored modules (`python3 -m
panopticon.docs`,
`python3 -m panopticon.init_repo`, etc.) never leaves compiled bytecode as an
untracked-but-visible
or accidentally-staged artifact in the child repo. This is written
unconditionally on every
bootstrap run, first-time and idempotent re-run alike, using the same
overwrite-in-place trust
model as the vendored modules themselves.

#### Scenario: Fresh bootstrap creates the gitignore alongside vendored modules

- **GIVEN** a child repo that has never run the bootstrap script before
- **WHEN** the bootstrap script vendors the local-tooling package
- **THEN** `panopticon/.gitignore` exists and contains `__pycache__/`

#### Scenario: Bytecode from running vendored modules is not tracked

- **GIVEN** a freshly bootstrapped child repo
- **WHEN** the user's agent runs `python3 -m panopticon.docs` (or any other
  vendored module),
  producing `panopticon/__pycache__/`
- **THEN** `git status` does not list anything under `panopticon/__pycache__/`
  as untracked

#### Scenario: Re-run does not duplicate or remove the entry

- **WHEN** the bootstrap script runs again on an already-bootstrapped repo
- **THEN** `panopticon/.gitignore` still exists, still contains exactly
  `__pycache__/`, and no
  duplicate or additional gitignore files are created

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

### Requirement: Orchestrating init skill

The template repo SHALL include a `panopticon-init` skill (name prefix
`panopticon-`, so the existing
skill-download step installs it into the child repo automatically with no
bootstrap script changes) that
runs the other Phase 2 skills and the Phase 3 finalization command in the
correct dependency order, from
a single invocation, while leaving each underlying skill independently invocable
on its own.

The order SHALL be:

1. `panopticon-interface-naming`
2. `panopticon-interface-extraction` — after step 1, since it depends on the
   naming pass
3. `panopticon-dependency-naming` — after step 2, since a
   `panopticon-dependency-of` hint links a
   dependency entry to an existing interface's canonical name, which requires
   the interface index
   built by step 2 to already exist
4. `panopticon-dependency-extraction` — after step 3, since it depends on the
   dependency naming
   pass, mirroring how interface-extraction depends on interface-naming
5. `panopticon-doc-generation` — after steps 1–4, since the interface-docs and
   dependency-docs
   layers are rendered from the local indices (`panopticon/index.json` and the
   dependency shard)
   that those steps build; running doc-generation first has no index to render
   from
6. The finalization command (`python3 -m panopticon.init_repo --instance
   <instance>`) — the instance
   slug SHALL be self-discovered by reading the `uses:` line already wired into
   `.github/workflows/panopticon-pr.yml`, rather than requiring the user to
   supply it

`panopticon-init` SHALL maintain a checkpoint log at `panopticon/.init-log.json`
recording which of the
six steps have completed. Before starting a step, it SHALL check the log and
skip any step already
recorded as complete. It SHALL update the log immediately after each step
completes, so an interrupted
run — including one resumed in a new agent session with no memory of the prior
one — continues from the
first incomplete step rather than restarting from scratch or skipping ahead into
a step whose
prerequisites aren't met. Once all six steps have completed and
`panopticon/config.json` has been
written, `panopticon-init` SHALL delete the checkpoint log — a completed
initialization has no further
use for it, and it SHALL NOT remain in the repo afterward.

Each of the six skills SHALL remain fully usable on its own, independent of
`panopticon-init` and of any
checkpoint log state, for users who want to run a single step directly.

#### Scenario: Fresh run starts at interface naming

- **GIVEN** no checkpoint log exists
- **WHEN** `/panopticon-init` runs
- **THEN** it starts with `panopticon-interface-naming`, then creates the
  checkpoint log recording that
  step's completion before continuing

#### Scenario: Dependency naming runs only after the interface index exists

- **GIVEN** the checkpoint log shows `panopticon-interface-naming` and
  `panopticon-interface-extraction`
  complete
- **WHEN** `panopticon-init` continues
- **THEN** it runs `panopticon-dependency-naming` next, with a populated
  interface index available for
  `panopticon-dependency-of` hints to reference

#### Scenario: Doc generation runs only after both indices exist

- **GIVEN** the checkpoint log shows `panopticon-interface-naming`,
  `panopticon-interface-extraction`,
  `panopticon-dependency-naming`, and `panopticon-dependency-extraction` all
  complete
- **WHEN** `panopticon-init` continues
- **THEN** it runs `panopticon-doc-generation` next, with a populated interface
  index and dependency
  shard to render `interfaces.md` and the dependency-docs layer from

#### Scenario: Resuming after an interrupted session

- **GIVEN** a checkpoint log recording `panopticon-interface-naming`,
  `panopticon-interface-extraction`,
  and `panopticon-dependency-naming` as complete, from a prior agent session
  that did not finish
- **WHEN** `/panopticon-init` is invoked again, in a new agent session with no
  memory of the prior one
- **THEN** it skips the three completed steps and resumes at
  `panopticon-dependency-extraction`

#### Scenario: Checkpoint log deleted on successful completion

- **GIVEN** all six steps have completed and `panopticon/config.json` has been
  written
- **WHEN** `panopticon-init` finishes
- **THEN** `panopticon/.init-log.json` no longer exists in the repo

#### Scenario: Individual skills remain independently invocable

- **WHEN** a user invokes `/panopticon-doc-generation` or
  `/panopticon-dependency-naming` directly
  instead of `/panopticon-init`
- **THEN** it runs as its own standalone skill, unaffected by whether a
  checkpoint log exists

#### Scenario: Finalization instance slug is self-discovered

- **WHEN** `panopticon-init` reaches the finalization step
- **THEN** it determines the instance slug by reading the `uses:` line in
  `.github/workflows/panopticon-pr.yml` rather than asking the user for it

### Requirement: Agent-driven initialization

Repo initialization SHALL follow a three-phase sequence:

**Phase 1 — Bootstrap (deterministic, no AI):** the bootstrap installer script
installs skills, vendors
the local-tooling subset of the `panopticon` Python package, and wires caller
workflows in the child
repo, then outputs the `/panopticon-init` prompt. No `PANOPTICON_LLM_*` or local
instance clone is
required.

**Phase 2 — Agent (AI-driven):** the user's preferred AI agent follows the
`panopticon-init` skill
invoked by the bootstrap script's printed prompt, which sequences the
interface-naming,
interface-extraction, dependency-naming, dependency-extraction, and
doc-generation skills in dependency
order (with a resumable checkpoint log) to build the local interface index
(`panopticon/index.json`), the local dependency shard, and generate the
four-layer documentation. No
`PANOPTICON_LLM_*` configuration is required locally; the agent uses its own
harness.

**Phase 3 — Finalization (deterministic):** the finalization step validates that
the agent-produced docs
and index meet requirements (all four layers present and following their
templates; schema-valid index)
and writes `panopticon/config.json` — the initialization flag — only after that
validation passes.
`panopticon/config.json` SHALL be the last artifact created during
initialization.

#### Scenario: Successful initialization

- **GIVEN** the bootstrap script has installed skills and workflows and printed
  the `/panopticon-init`
  prompt
- **WHEN** the agent has generated docs and indices and the finalization step
  runs
- **THEN** `panopticon/config.json` is written as the final artifact, and the
  repo is fully initialized

#### Scenario: Agent output incomplete at finalization

- **WHEN** the finalization step runs before the agent has produced all four
  documentation layers
- **THEN** no config file is written and the tooling reports exactly which
  requirements are unmet

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

### Requirement: Org-level CI prerequisites

The init tooling SHALL derive required org-level Actions secrets and variables
from the validated instance
provider contract, including the configured instance-token name, provider
credentials, model and endpoint
or selected credential-mode settings, and bounded request/job budget names.
These values are consumed only
by shared CI workflows. Child repos MUST NOT require per-repo secret or variable
configuration; generated
callers SHALL map org-level names explicitly to canonical provider workflow
inputs and secrets. Missing
values SHALL NOT block documentation or index initialization, but provider
configuration itself MUST be
valid before bootstrap writes any child artifact.

Verifying org-level secrets and variables requires a GitHub auth token with
permission to read org-level
Actions secrets and variables. With a resolved `GH_TOKEN`, `GITHUB_TOKEN`, or
`gh auth token`, tooling SHALL
query the org APIs and report every missing provider-resolved name and its kind.
Without such a token,
tooling SHALL report no auth error and SHALL print the visible org Actions
settings URL plus equivalent
`gh secret list --org` and `gh variable list --org` commands, listing every
provider-resolved name to check.

#### Scenario: Configured instance token is missing

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization checks an org missing the instance-token secret name
  recorded by the instance
- **THEN** it reports that exact org-level secret name and how to configure it

#### Scenario: Configured provider variable is missing

- **GIVEN** a GitHub auth token is available
- **WHEN** initialization checks an org missing a variable required by the
  selected provider contract
- **THEN** it reports that exact variable name and its provider purpose

#### Scenario: Instance-managed credentials need no AWS variables

- **WHEN** initialization checks an instance using Bedrock `instance-managed`
  credentials
- **THEN** it does not report an AWS region or role-ARN variable as a missing
  prerequisite

#### Scenario: Auth token available

- **GIVEN** a GitHub auth token is resolved from `GH_TOKEN`, `GITHUB_TOKEN`, or
  `gh auth token`
- **WHEN** the org-level prerequisite check runs
- **THEN** it queries the org APIs and reports exactly which provider-resolved
  names are absent

#### Scenario: No auth token available

- **GIVEN** no GitHub auth token can be resolved
- **WHEN** the org-level prerequisite check runs
- **THEN** it prints the visible web UI URL, equivalent listing commands, and
  every provider-resolved secret
  and variable name without treating the missing auth token as an initialization
  failure

### Requirement: Documentation location adoption

When the child repo already has documentation, initialization SHALL adopt that
location as the
documentation source. When no documentation exists, the user SHALL be prompted
for the desired location,
with `docs/` as the default. The chosen location SHALL be recorded in
`panopticon/config.json`.

#### Scenario: Repo with existing docs

- **WHEN** the finalization step runs on a repo with an existing documentation
  folder
- **THEN** that folder is configured as the doc source

#### Scenario: Repo without docs

- **WHEN** the finalization step runs on a repo with no existing documentation
- **THEN** the user is prompted for the desired location, defaulting to `docs/`

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

### Requirement: Idempotent re-initialization

Re-running the bootstrap script or the finalization step on an
already-initialized repo SHALL update all
artifacts in place without creating duplicates.

#### Scenario: Re-run bootstrap on initialized repo

- **WHEN** the bootstrap script runs again on a repo that already has Panopticon
  skills, vendored local
  tooling, and workflows
- **THEN** skills (at the previously chosen location), the vendored
  `panopticon/` modules, and workflows
  are refreshed in place and no duplicates are created

#### Scenario: Re-run finalization on initialized repo

- **WHEN** the finalization step runs again on a repo that already has
  `panopticon/config.json`
- **THEN** the config is updated in place and no duplicate files are created

### Requirement: Child bootstrap validates provider configuration before writing

The child bootstrap installer SHALL fetch and strictly validate the instance's
provider configuration
before selecting a skills location, downloading content, vendoring tooling, or
writing workflows. It SHALL
distinguish an inaccessible config, malformed config, missing provider, unknown
provider, invalid configured
name, and selected workflow absent at `workflow_ref`. Any such failure MUST
leave all child files untouched.

#### Scenario: Instance provider is unset

- **WHEN** child bootstrap reads a valid instance config with no selected
  provider
- **THEN** it exits non-zero with console and CLI instance-configuration
  instructions and writes no child
  files

#### Scenario: Selected provider workflow is absent at the configured ref

- **WHEN** the instance config selects Bedrock but the selected `workflow_ref`
  lacks the registered Bedrock
  workflow
- **THEN** bootstrap fails before writing, names the missing path and ref, and
  explains how to select a ref
  containing the provider workflow

#### Scenario: Instance config cannot be fetched

- **WHEN** the GitHub API cannot retrieve `panopticon.config.json`
- **THEN** bootstrap reports the access or transport failure instead of treating
  it as empty configuration

### Requirement: Child bootstrap generates only the selected provider caller

The child SHALL retain a stable local `.github/workflows/panopticon-pr.yml`
caller. Bootstrap SHALL point
that caller at only the provider workflow selected by live instance
configuration and SHALL emit explicit
canonical input and secret mappings from the configured org-level names, the
exact permissions required by
that provider workflow, the selected trusted credential mode, and the effective
configuration revision. It
SHALL map AWS region and role-ARN variables only for Bedrock `github-oidc` mode.
It SHALL NOT copy
unselected provider workflows into the child or use blanket `secrets: inherit`.

#### Scenario: Bedrock child caller generated

- **WHEN** the instance selects Bedrock and child bootstrap succeeds
- **THEN** the local PR caller references the instance's Bedrock reusable
  workflow, grants `id-token: write`,
  maps the configured instance-token secret and Bedrock variables explicitly,
  and includes the config
  revision

#### Scenario: LiteLLM child caller generated

- **WHEN** the instance selects LiteLLM and child bootstrap succeeds
- **THEN** the local PR caller references only the instance's LiteLLM workflow,
  omits Bedrock-only setup,
  and maps the configured endpoint, model, API-key, and budget names explicitly

#### Scenario: Instance-managed Bedrock child caller generated

- **WHEN** the instance selects Bedrock `instance-managed` credentials and child
  bootstrap succeeds
- **THEN** the local caller records that credential mode, maps no AWS region or
  role-ARN variable, and
  references the selected instance workflow only

### Requirement: Stale caller remediation prints an exact installer command

Every bootstrap or workflow failure caused by stale provider, secret-name,
variable-name, or revision SHALL
explain the cause and print a copy/paste child-bootstrap command using the
resolved instance
slug. The command SHALL set `PANOPTICON_INSTANCE` on the piped Python process
itself, without an `export`,
and SHALL instruct the user to run it from inside the child clone, review and
commit the generated changes,
push them, and rerun or await the PR workflow.

#### Scenario: Renamed instance-token secret leaves old caller empty

- **WHEN** an existing caller maps a removed old instance-token secret name and
  the reusable workflow
  receives an empty canonical token
- **THEN** it fails before instance checkout and prints the exact
  public-installer command for that child’s
  recorded instance plus the commit, push, and rerun instructions

### Requirement: Recovery formatter preserves pre-bootstrap compatibility

The child bootstrap installer SHALL vendor a standard-library recovery formatter
after provider validation
succeeds. Provider workflows SHALL use the shared formatter to render stale or
missing-provider recovery
output. Bootstrap failures that occur before vendoring, and the legacy caller
guard, SHALL render equivalent
self-contained recovery output without importing the child-vendored formatter.

#### Scenario: Successful bootstrap makes the formatter available

- **WHEN** child bootstrap validates the selected provider contract and
  completes successfully
- **THEN** the child repository contains the recovery formatter for subsequent
  provider workflow runs

#### Scenario: Unconfigured instance fails before vendoring

- **WHEN** child bootstrap resolves an instance with no configured provider
- **THEN** it prints complete configuration and child-bootstrap recovery
  instructions without requiring the
  child repository to contain the recovery formatter

#### Scenario: Legacy caller lacks the formatter

- **WHEN** a child generated before recovery-formatting vendoring invokes the
  legacy caller guard
- **THEN** the guard prints complete configuration and child-bootstrap recovery
  instructions without an
  import failure

### Requirement: Template sync uses a shared repairable workflow

The instance `sync-from-template.yml` SHALL be a minimal, fixed caller that
invokes only the template-owned
reusable workflow `.github/workflows/shared-template-sync-caller-only.yml` from
`industrial-curiosity/panopticon-ay-eye@main`. The shared workflow SHALL check
out and update the calling
instance repository, retain the `PANOPTICON_INSTANCE_TOKEN` fallback and
pre-push validation contract, and
keep all merge, protected-path, and recovery logic in the template repository.
The instance caller SHALL
not duplicate that logic or accept a configurable repository, workflow path, or
ref. It SHALL pass the
optional instance-token secret explicitly and SHALL NOT expose either token
value. On every sync failure,
the shared workflow SHALL write a step-summary recovery section with commands
for performing the sync from
a local clone of the instance repository: fetch the fixed template remote,
perform the equivalent merge,
resolve any conflict, review the result, commit, and push. The shared workflow
filename SHALL identify it
as shared and caller-only, and it SHALL accept only `workflow_call` rather than
a direct trigger.

User-facing documentation SHALL explain that the sync preserves every exact path
listed in
`protected_paths`, the protected diagram configuration, and an existing
generated
`docs/architecture.md`. It SHALL also explain that other customized
template-managed files can receive a
template update or produce a merge conflict, and that `protected_paths` does not
protect child-repository
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
  instructions for a GitHub token secret
  with Contents and Workflows read/write permission

#### Scenario: Shared sync fails

- **WHEN** the shared sync workflow fails during checkout, fetch, merge,
  validation, or push
- **THEN** its step summary contains a local instance-repository recovery
  section with the fixed template
  remote, equivalent merge, conflict-resolution, review, commit, and push
  commands

#### Scenario: Shared sync caller cannot be redirected

- **WHEN** instance configuration or workflow-dispatch input attempts to select
  another sync repository,
  workflow path, or ref
- **THEN** the caller rejects the unsupported configuration and invokes no
  alternative workflow

#### Scenario: Shared workflow is not directly runnable

- **WHEN** a user views the template workflow list
- **THEN** the shared workflow is named `shared-template-sync-caller-only.yml`
  and has no direct trigger
  such as `workflow_dispatch`

#### Scenario: Maintainer protects an instance customization

- **GIVEN** an instance customizes a template-managed skill or workflow
- **WHEN** its maintainer adds that exact path to `protected_paths` and runs the
  template sync
- **THEN** the sync preserves the instance copy and the setup documentation
  explains that the same setting
  does not protect child-repository tooling syncs

#### Scenario: Maintainer has an unprotected instance customization

- **GIVEN** an instance customizes a template-managed file that is absent from
  `protected_paths`
- **WHEN** the template also changes that file during sync
- **THEN** the setup documentation explains that Git may update the file or
  report a merge conflict for
  local resolution

### Requirement: README provides concise project orientation

The README SHALL provide a quickly scannable overview of the project's purpose,
repository roles, primary
workflow, and links to the setup guide and other detailed documentation. It
SHALL use clear sections that
separate at-a-glance orientation from navigation. Detailed setup instructions,
configuration reference,
implementation inventories, and operational procedures SHALL live in
purpose-named documentation files
rather than in the README. The README SHALL NOT include temporary implementation
status, incomplete-work
notes, or feature-wiring details. At the top of the README, it SHALL retain the
project logo and an obvious
link to the organization's architecture documentation. At the end of the README,
it SHALL display a
thumbnail for the specified Panopticon YouTube video that opens
`https://www.youtube.com/watch?v=sIJ9XhBSkI8` in a new browser tab or window.

#### Scenario: New maintainer opens the README

- **WHEN** a maintainer reads the README for the first time
- **THEN** they can understand Panopticon's purpose, the template/instance/child
  roles, and the primary
  lifecycle at a glance, then follow clearly labelled links for setup and deeper
  reference

#### Scenario: Maintainer finds the organization architecture

- **WHEN** a maintainer opens the README
- **THEN** they see the project logo and an obvious link to
  `docs/architecture.md` before the detailed
  orientation and navigation sections

#### Scenario: Reader needs detailed setup or configuration

- **WHEN** a reader needs instructions for configuring an instance,
  synchronizing a template, or using a
  feature in detail
- **THEN** the README directs them to a purpose-named guide instead of embedding
  the detailed procedure

#### Scenario: A feature has incomplete automation

- **WHEN** an implementation detail or workflow integration is incomplete
- **THEN** the README does not include its status, workaround, or follow-up
  description

#### Scenario: Reader reaches the end of the README

- **WHEN** a reader reaches the end of the README
- **THEN** they see the thumbnail at
  `https://img.youtube.com/vi/sIJ9XhBSkI8/hqdefault.jpg` in an anchor
  with `target="_blank"` that opens
  `https://www.youtube.com/watch?v=sIJ9XhBSkI8` in a new browser tab or
  window
