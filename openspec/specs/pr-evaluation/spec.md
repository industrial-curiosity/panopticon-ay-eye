### Requirement: Initialization check

The PR workflow SHALL verify that the repo is Panopticon-initialized (`panopticon/config.json` present); when
it is not, the check SHALL fail with an actionable message pointing at the init procedure.

#### Scenario: Uninitialized repo

- **WHEN** a PR runs in a repo without `panopticon/config.json`
- **THEN** the check fails, reporting that the repo is not initialized and how to initialize it, and remaining
  Panopticon checks are skipped

### Requirement: Bounded PR-evaluation job duration

The reusable PR-evaluation workflow SHALL set an explicit timeout for its evaluate job from the optional
org-level Actions variable `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES`, using 20 minutes when the variable is unset.
The setup guide SHALL document that the variable accepts a whole number from 10 through 60 and is evaluated by
GitHub Actions before the job starts.

#### Scenario: Default evaluate-job duration

- **WHEN** the PR-evaluation workflow runs without `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES`
- **THEN** GitHub Actions terminates the evaluate job after 20 minutes if it has not completed

#### Scenario: Configured evaluate-job duration

- **WHEN** the organization sets `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES` to a valid whole number from 10 through 60
- **THEN** GitHub Actions uses that number as the evaluate job timeout in minutes

### Requirement: Pre-merge index simulation

The PR workflow SHALL verify that the PR branch's committed local index is current — the CI agent evaluates
what changed in the PR plus the minimal context required to understand it, and a stale index fails the check
naming what must be updated — then fetch the compiled index from the instance repo's default branch using
`PANOPTICON_INSTANCE_TOKEN` and run the merge logic in dry-run mode against the committed index. Detected
conflicts SHALL be posted as a PR comment and in the CI summary. Simulation MUST use the same merge code path
as the real merge.

#### Scenario: PR introduces a conflicting interface change

- **WHEN** a PR changes an interface in a way that would create a conflict entry at merge time
- **THEN** the simulation posts a PR comment describing the conflict before merge

#### Scenario: PR with no interface impact

- **WHEN** a PR touches no interfaces
- **THEN** the simulation reports no conflicts and does not post a conflict comment

### Requirement: Branch state push

The PR workflow SHALL push the PR's generated docs and local index state to a branch named `{repo}/{branch}`
in the instance repo (verbatim, no escaping), so in-flight branch state is visible org-wide. The workflow MUST
NOT touch the instance repo's default branch.

#### Scenario: PR opened or updated

- **WHEN** a PR workflow runs for branch `feature/x` of repo `svc-a`
- **THEN** the instance repo branch `svc-a/feature/x` contains that branch's docs and index state

### Requirement: Org-configurable gating

Default check outcomes SHALL be: initialization and doc-drift checks fail the workflow when they detect a
problem, so the developer knows what to fix; interface-conflict checks are advisory (reported, not failing)
because LLM-extracted entries can produce false positives; the diagram-existence check defaults to advisory so
existing initialized repos are not immediately blocked the moment this check ships, since they have not yet
backfilled a diagram section. The instance repo's `panopticon.config.json` SHALL allow orgs to adjust each
check type (init, doc-drift, interface-conflict, diagram-missing) between advisory and blocking. Workflows
MUST read gating configuration rather than hardcoding outcomes.

#### Scenario: Interface conflicts advisory by default

- **WHEN** a conflict is detected and the org has not changed gating configuration
- **THEN** the check reports the conflict but the workflow succeeds

#### Scenario: Stale docs fail by default

- **WHEN** the drift check finds stale docs and the org has not changed gating configuration
- **THEN** the workflow fails with the drift report

#### Scenario: Org escalates conflicts to blocking

- **WHEN** `panopticon.config.json` marks interface-conflict checks as blocking and a conflict is detected
- **THEN** the check fails so branch protection can block the merge

#### Scenario: Missing diagram is advisory by default

- **WHEN** the diagram-existence check finds no diagram section and the org has not changed gating
  configuration
- **THEN** the check reports the finding but the workflow succeeds

#### Scenario: Org escalates missing diagrams to blocking

- **WHEN** `panopticon.config.json` marks `diagram-missing` as blocking and a repo's PR has no diagram section
- **THEN** the check fails so branch protection can block the merge

### Requirement: Combined report leads with a de-duplicated action list

The PR workflow's combined report SHALL open with a "TL;DR" section listing
the concrete actions a developer must take to resolve everything the checks found, before any per-check
detail — built from the same doc-drift, index-currency, diagram-existence, and pre-merge-simulation findings.
Every doc-drift, index-currency, and diagram-existence finding SHALL collapse
into a single TL;DR action — regardless of how many docs are stale, whether the index itself is also stale,
or whether the diagram section is missing or stale — instructing the developer to run the
panopticon-doc-generation skill once, since that skill's own rules already keep the index current, regenerate
every stale doc, and produce the diagram section in the same pass; the TL;DR MUST NOT list a separate line per
stale doc, a separate line for the index update, or a separate line for a missing/stale diagram. Interface
conflicts from pre-merge simulation are a distinct concern — resolving cross-repo ownership/naming, not
something a single doc-generation pass fixes — and remain their own action(s), never folded into the
doc-generation line. The same TL;DR SHALL be repeated verbatim at the end of the report, after the per-check
detail, so it's visible whether a reader scans from the top or scrolls to the bottom. When every check passes,
the TL;DR SHALL say so plainly instead of listing actions.

#### Scenario: Many stale docs and a stale index collapse into one action

- **GIVEN** a PR leaves five docs stale and the local index stale for the same underlying reason
- **WHEN** the combined report is built
- **THEN** the TL;DR contains exactly one line instructing the developer to run the panopticon-doc-generation
  skill once — not one line per stale doc plus a separate line for the index — and each check's own detailed
  section below still shows its own full finding

#### Scenario: Interface conflicts stay a separate action

- **GIVEN** a PR both leaves docs stale and introduces an interface conflict
- **WHEN** the combined report is built
- **THEN** the TL;DR contains one line for running panopticon-doc-generation and a separate line for resolving
  the conflict — the two are never merged into a single instruction

#### Scenario: TL;DR appears at both ends of the report

- **GIVEN** one or more checks found actionable problems
- **WHEN** the combined report is generated
- **THEN** the same TL;DR action list appears before the per-check detail and again, identically, after it

#### Scenario: All checks pass

- **GIVEN** doc-drift, index-currency, diagram-existence, and pre-merge simulation all pass
- **WHEN** the combined report is generated
- **THEN** the TL;DR states plainly that everything passed, with no action items, at both the top and bottom
  of the report

#### Scenario: Missing diagram collapses into the same doc-generation action

- **GIVEN** a PR leaves docs stale and also has no diagram section
- **WHEN** the combined report is built
- **THEN** the TL;DR contains exactly one line instructing the developer to run panopticon-doc-generation once
  — the missing diagram does not add a second line

### Requirement: CI checks distinguish operational failure from a business verdict by exit code

Every LLM-backed PR-evaluation check (doc-drift, index-currency) SHALL use a fixed exit-code contract: `0`
means the check ran successfully and found no issue; `2` means the check ran successfully and found an
actionable issue (stale docs, a stale index); any other exit code — including whatever an uncaught exception
produces by default in the check's language runtime — SHALL be treated by the calling workflow as an
operational failure: the check did not complete and its outcome is unknown, never a verdict. `1` SHALL NOT
be used to mean either outcome, since it collides with the exit code most language runtimes (including
Python) already use by default for any uncaught exception, making a genuine crash indistinguishable from a
deliberate "stale" result. This mirrors the pre-merge-simulation check's existing exit-code convention
(`0`/`2`/anything-else), which does not have this collision.

Every code path that can produce an operational failure — a malformed LLM response, a missing or
unreachable endpoint, or any other exception raised while producing the verdict — SHALL be caught explicitly
and turned into a non-`0`/non-`2` exit paired with a clear `::error::`-annotated message naming what
happened, rather than left to crash with an unhandled exception whose exit code the calling workflow cannot
distinguish from a real verdict.

#### Scenario: Malformed LLM response is an operational failure, not a stale verdict

- **GIVEN** the LLM endpoint returns a response that fails to parse as the expected verdict JSON
- **WHEN** the doc-drift or index-currency check runs
- **THEN** the check exits with a code that is neither `0` nor `2`, the workflow fails loudly with an
  `::error::` message identifying the parse failure, and no report or TL;DR action is generated implying a
  real "stale" finding

#### Scenario: Genuine stale verdict still exits with the reserved code

- **GIVEN** the LLM endpoint returns a well-formed verdict indicating stale docs or a stale index
- **WHEN** the check runs
- **THEN** it exits `2`, the workflow proceeds to the combined report, and gating applies normally

### Requirement: Checks run independently regardless of earlier failures; gating decides at the end

Doc-drift, index-currency, and pre-merge simulation SHALL each attempt to run regardless of whether an
earlier check found a business verdict (clean or stale) or suffered an operational failure — no check's
outcome, including a crash, SHALL prevent a later, independent check from running and reporting its own
result. The combined report SHALL reflect every check's own actual outcome: a check that could not
complete SHALL have its own section stating so clearly (naming the check and the operational failure),
distinct from a check that ran and passed — the combined report MUST NOT silently omit a check whose step
ran, and MUST NOT let one check's operational failure make the report imply that other checks, or the
whole PR, passed. Gating (the final step) SHALL fail the workflow when any check had an operational
failure, in addition to its existing rules for blocking business verdicts — an operational failure is
never merely advisory, since a check that could not run has told the developer nothing they can act on.

#### Scenario: One check's operational failure does not block a later, independent check from running

- **GIVEN** the doc-drift check suffers an operational failure (e.g. a malformed LLM response)
- **WHEN** the PR workflow continues
- **THEN** the index-currency check and pre-merge simulation still run and report their own real outcomes

#### Scenario: Combined report shows the failed check's own status, not silence or false success

- **GIVEN** doc-drift operationally failed while index-currency and simulation both passed cleanly
- **WHEN** the combined report is built
- **THEN** it shows doc-drift's own section stating it could not run and why, alongside index-currency's and
  simulation's real "passed" sections — it never claims "all checks passed" while a check crashed, and never
  omits the crashed check's status entirely

#### Scenario: An operational failure always fails the workflow

- **GIVEN** any one check had an operational failure, regardless of what the other checks found
- **WHEN** gating is applied
- **THEN** the workflow fails — an operational failure is never treated as advisory, even for checks whose
  business verdict would otherwise be advisory-by-default

### Requirement: Diagram-existence check

The PR workflow SHALL verify, deterministically and without any LLM call, that the repo's `architecture.md`
contains a `## Architecture diagram` section with exactly one fenced code block tagged with the instance's
configured diagram format (architecture-diagrams capability). This check is independent of doc-drift: it
verifies existence and structure only, never diagram accuracy. It SHALL run after the instance repo is
checked out (so it can read the configured format from `panopticon.diagram.config.json`) and requires no
`PANOPTICON_LLM_*` configuration.

#### Scenario: Diagram section missing

- **WHEN** a PR's `architecture.md` has no `## Architecture diagram` section, or that section has no fenced
  code block in the configured format
- **THEN** the check fails, naming the missing section and the exact skill/command that adds it
  (`panopticon-doc-generation`)

#### Scenario: Diagram section present and well-formed

- **WHEN** a PR's `architecture.md` contains a `## Architecture diagram` section with a fenced code block in
  the configured format
- **THEN** the check passes without invoking an LLM

### Requirement: Tooling-currency PR check

The PR workflow SHALL run the workflow-ref alignment check and the skills/tooling drift check
(tooling-currency capability) after the instance repo is checked out, using that same checkout —
no additional network calls, no GitHub API usage, no LLM involvement. These checks SHALL run for
every initialized repo's PR, independent of every other check's outcome, and SHALL NOT participate
in the org config's gating mechanism or the PR workflow's combined TL;DR report (tooling-currency
capability: "Tooling-currency checks are always advisory").

#### Scenario: Tooling-currency checks run alongside the other PR checks

- **WHEN** a PR workflow runs for an initialized repo
- **THEN** the workflow-ref alignment check and the skills/tooling drift check both run after the
  instance repo checkout step, independent of whether doc-drift, index-currency, diagram-existence,
  or pre-merge simulation found problems

#### Scenario: Tooling-currency drift does not affect the workflow's outcome

- **GIVEN** the workflow-ref alignment check and the skills/tooling drift check both find drift
- **WHEN** the PR workflow's final gating step runs
- **THEN** the workflow's pass/fail outcome is unaffected by either finding
