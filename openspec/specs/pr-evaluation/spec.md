# PR evaluation

## Purpose

Define the reusable pull-request workflow that evaluates Panopticon-managed
repositories.

## Requirements

### Requirement: Initialization check

The PR workflow SHALL verify that the repo is Panopticon-initialized
(`panopticon/config.json` present); when
it is not, the check SHALL fail with an actionable message pointing at the init
procedure.

#### Scenario: Uninitialized repo

- **WHEN** a PR runs in a repo without `panopticon/config.json`
- **THEN** the check fails, reporting that the repo is not initialized and how
  to initialize it, and remaining
  Panopticon checks are skipped

### Requirement: Bounded PR-evaluation job duration

Each provider-specific reusable PR-evaluation workflow SHALL set an explicit
timeout for its evaluate job
from the canonical workflow input mapped by child bootstrap from the configured
org-level job-timeout
variable name, using 20 minutes when the mapped value is unset. The setup guide
SHALL document that the
value accepts a whole number from 10 through 60 and is evaluated by GitHub
Actions before the job starts.

#### Scenario: Default evaluate-job duration

- **WHEN** a provider-specific PR workflow receives no mapped job-timeout value
- **THEN** GitHub Actions terminates the evaluate job after 20 minutes if it has
  not completed

#### Scenario: Configured evaluate-job duration

- **WHEN** child bootstrap maps a configured org variable whose value is a whole
  number from 10 through 60
- **THEN** the selected provider workflow uses that number as its evaluate job
  timeout in minutes

### Requirement: Pre-merge index simulation

The PR workflow SHALL verify that the PR branch's committed local index is
current — the CI agent evaluates
what changed in the PR plus the minimal context required to understand it, and a
stale index fails the check
naming what must be updated — then fetch the compiled index from the instance
repo's default branch using
`PANOPTICON_INSTANCE_TOKEN` and run the merge logic in dry-run mode against the
committed index. Detected
conflicts SHALL be posted as a PR comment and in the CI summary. Simulation MUST
use the same merge code path
as the real merge.

#### Scenario: PR introduces a conflicting interface change

- **WHEN** a PR changes an interface in a way that would create a conflict entry
  at merge time
- **THEN** the simulation posts a PR comment describing the conflict before
  merge

#### Scenario: PR with no interface impact

- **WHEN** a PR touches no interfaces
- **THEN** the simulation reports no conflicts and does not post a conflict
  comment

### Requirement: Branch state push

The PR workflow SHALL push the PR's generated docs and local index state to a
branch named `{repo}/{branch}`
in the instance repo (verbatim, no escaping), so in-flight branch state is
visible org-wide. The workflow MUST
NOT touch the instance repo's default branch.

#### Scenario: PR opened or updated

- **WHEN** a PR workflow runs for branch `feature/x` of repo `svc-a`
- **THEN** the instance repo branch `svc-a/feature/x` contains that branch's
  docs and index state

### Requirement: Org-configurable gating

Default check outcomes SHALL be: initialization and doc-drift checks fail the
workflow when they detect a
problem, so the developer knows what to fix; interface-conflict checks are
advisory (reported, not failing)
because LLM-extracted entries can produce false positives; the diagram-existence
check defaults to advisory so
existing initialized repos are not immediately blocked the moment this check
ships, since they have not yet
backfilled a diagram section. The instance repo's `panopticon.config.json` SHALL
allow orgs to adjust each
check type (init, doc-drift, interface-conflict, diagram-missing) between
advisory and blocking. Workflows
MUST read gating configuration rather than hardcoding outcomes.

#### Scenario: Interface conflicts advisory by default

- **WHEN** a conflict is detected and the org has not changed gating
  configuration
- **THEN** the check reports the conflict but the workflow succeeds

#### Scenario: Stale docs fail by default

- **WHEN** the drift check finds stale docs and the org has not changed gating
  configuration
- **THEN** the workflow fails with the drift report

#### Scenario: Org escalates conflicts to blocking

- **WHEN** `panopticon.config.json` marks interface-conflict checks as blocking
  and a conflict is detected
- **THEN** the check fails so branch protection can block the merge

#### Scenario: Missing diagram is advisory by default

- **WHEN** the diagram-existence check finds no diagram section and the org has
  not changed gating
  configuration
- **THEN** the check reports the finding but the workflow succeeds

#### Scenario: Org escalates missing diagrams to blocking

- **WHEN** `panopticon.config.json` marks `diagram-missing` as blocking and a
  repo's PR has no diagram section
- **THEN** the check fails so branch protection can block the merge

### Requirement: Combined report leads with a de-duplicated action list

The PR workflow's combined report SHALL open with a "TL;DR" section listing
the concrete actions a developer must take to resolve everything the checks
found, before any per-check
detail — built from the same doc-drift, index-currency, diagram-existence, and
pre-merge-simulation findings.
Every doc-drift, index-currency, and diagram-existence finding SHALL collapse
into a single TL;DR action — regardless of how many docs are stale, whether the
index itself is also stale,
or whether the diagram section is missing or stale — instructing the developer
to run the
panopticon-doc-generation skill once, since that skill's own rules already keep
the index current, regenerate
every stale doc, and produce the diagram section in the same pass; the TL;DR
MUST NOT list a separate line per
stale doc, a separate line for the index update, or a separate line for a
missing/stale diagram. Interface
conflicts from pre-merge simulation are a distinct concern — resolving
cross-repo ownership/naming, not
something a single doc-generation pass fixes — and remain their own action(s),
never folded into the
doc-generation line. The same TL;DR SHALL be repeated verbatim at the end of the
report, after the per-check
detail, so it's visible whether a reader scans from the top or scrolls to the
bottom. When every check passes,
the TL;DR SHALL say so plainly instead of listing actions.

#### Scenario: Many stale docs and a stale index collapse into one action

- **GIVEN** a PR leaves five docs stale and the local index stale for the same
  underlying reason
- **WHEN** the combined report is built
- **THEN** the TL;DR contains exactly one line instructing the developer to run
  the panopticon-doc-generation
  skill once — not one line per stale doc plus a separate line for the index —
  and each check's own detailed
  section below still shows its own full finding

#### Scenario: Interface conflicts stay a separate action

- **GIVEN** a PR both leaves docs stale and introduces an interface conflict
- **WHEN** the combined report is built
- **THEN** the TL;DR contains one line for running panopticon-doc-generation and
  a separate line for resolving
  the conflict — the two are never merged into a single instruction

#### Scenario: TL;DR appears at both ends of the report

- **GIVEN** one or more checks found actionable problems
- **WHEN** the combined report is generated
- **THEN** the same TL;DR action list appears before the per-check detail and
  again, identically, after it

#### Scenario: All checks pass

- **GIVEN** doc-drift, index-currency, diagram-existence, and pre-merge
  simulation all pass
- **WHEN** the combined report is generated
- **THEN** the TL;DR states plainly that everything passed, with no action
  items, at both the top and bottom
  of the report

#### Scenario: Missing diagram collapses into the same doc-generation action

- **GIVEN** a PR leaves docs stale and also has no diagram section
- **WHEN** the combined report is built
- **THEN** the TL;DR contains exactly one line instructing the developer to run
  panopticon-doc-generation once
  — the missing diagram does not add a second line

### Requirement: CI checks distinguish operational failure from a business verdict by exit code

Every LLM-backed PR-evaluation check (doc-drift, index-currency) SHALL use a
fixed exit-code contract: `0`
means the check ran successfully and found no issue; `2` means the check ran
successfully and found an
actionable issue (stale docs, a stale index); any other exit code — including
whatever an uncaught exception
produces by default in the check's language runtime — SHALL be treated by the
calling workflow as an
operational failure: the check did not complete and its outcome is unknown,
never a verdict. `1` SHALL NOT
be used to mean either outcome, since it collides with the exit code most
language runtimes (including
Python) already use by default for any uncaught exception, making a genuine
crash indistinguishable from a
deliberate "stale" result. This mirrors the pre-merge-simulation check's
existing exit-code convention
(`0`/`2`/anything-else), which does not have this collision.

Every code path that can produce an operational failure — a malformed LLM
response, a missing or
unreachable endpoint, or any other exception raised while producing the verdict
— SHALL be caught explicitly
and turned into a non-`0`/non-`2` exit paired with a clear `::error::`-annotated
message naming what
happened, rather than left to crash with an unhandled exception whose exit code
the calling workflow cannot
distinguish from a real verdict.

#### Scenario: Malformed LLM response is an operational failure, not a stale verdict

- **GIVEN** the LLM endpoint returns a response that fails to parse as the
  expected verdict JSON
- **WHEN** the doc-drift or index-currency check runs
- **THEN** the check exits with a code that is neither `0` nor `2`, the workflow
  fails loudly with an
  `::error::` message identifying the parse failure, and no report or TL;DR
  action is generated implying a
  real "stale" finding

#### Scenario: Genuine stale verdict still exits with the reserved code

- **GIVEN** the LLM endpoint returns a well-formed verdict indicating stale docs
  or a stale index
- **WHEN** the check runs
- **THEN** it exits `2`, the workflow proceeds to the combined report, and
  gating applies normally

### Requirement: Checks run independently regardless of earlier failures; gating decides at the end

Doc-drift, index-currency, and pre-merge simulation SHALL each attempt to run
regardless of whether an
earlier check found a business verdict (clean or stale) or suffered an
operational failure — no check's
outcome, including a crash, SHALL prevent a later, independent check from
running and reporting its own
result. The combined report SHALL reflect every check's own actual outcome: a
check that could not
complete SHALL have its own section stating so clearly (naming the check and the
operational failure),
distinct from a check that ran and passed — the combined report MUST NOT
silently omit a check whose step
ran, and MUST NOT let one check's operational failure make the report imply that
other checks, or the
whole PR, passed. Gating (the final step) SHALL fail the workflow when any check
had an operational
failure, in addition to its existing rules for blocking business verdicts — an
operational failure is
never merely advisory, since a check that could not run has told the developer
nothing they can act on.

#### Scenario: One check's operational failure does not block a later, independent check from running

- **GIVEN** the doc-drift check suffers an operational failure (e.g. a malformed
  LLM response)
- **WHEN** the PR workflow continues
- **THEN** the index-currency check and pre-merge simulation still run and
  report their own real outcomes

#### Scenario: Combined report shows the failed check's own status, not silence or false success

- **GIVEN** doc-drift operationally failed while index-currency and simulation
  both passed cleanly
- **WHEN** the combined report is built
- **THEN** it shows doc-drift's own section stating it could not run and why,
  alongside index-currency's and
  simulation's real "passed" sections — it never claims "all checks passed"
  while a check crashed, and never
  omits the crashed check's status entirely

#### Scenario: An operational failure always fails the workflow

- **GIVEN** any one check had an operational failure, regardless of what the
  other checks found
- **WHEN** gating is applied
- **THEN** the workflow fails — an operational failure is never treated as
  advisory, even for checks whose
  business verdict would otherwise be advisory-by-default

### Requirement: Diagram-existence check

The PR workflow SHALL verify, deterministically and without any LLM call, that
the repo's `architecture.md`
contains a `## Architecture diagram` section with exactly one fenced code block
tagged with the instance's
configured diagram format (architecture-diagrams capability). This check is
independent of doc-drift: it
verifies existence and structure only, never diagram accuracy. It SHALL run
after the instance repo is
checked out (so it can read the configured format from
`panopticon.diagram.config.json`) and requires no
`PANOPTICON_LLM_*` configuration.

#### Scenario: Diagram section missing

- **WHEN** a PR's `architecture.md` has no `## Architecture diagram` section, or
  that section has no fenced
  code block in the configured format
- **THEN** the check fails, naming the missing section and the exact
  skill/command that adds it
  (`panopticon-doc-generation`)

#### Scenario: Diagram section present and well-formed

- **WHEN** a PR's `architecture.md` contains a `## Architecture diagram` section
  with a fenced code block in
  the configured format
- **THEN** the check passes without invoking an LLM

### Requirement: Tooling-currency PR check

The PR workflow SHALL run the workflow-ref alignment check and the
skills/tooling drift check
(tooling-currency capability) after the instance repo is checked out, using that
same checkout —
no additional network calls, no GitHub API usage, no LLM involvement. These
checks SHALL run for
every initialized repo's PR, independent of every other check's outcome, and
SHALL NOT participate
in the org config's gating mechanism or the PR workflow's combined TL;DR report
(tooling-currency
capability: "Tooling-currency checks are always advisory").

#### Scenario: Tooling-currency checks run alongside the other PR checks

- **WHEN** a PR workflow runs for an initialized repo
- **THEN** the workflow-ref alignment check and the skills/tooling drift check
  both run after the
  instance repo checkout step, independent of whether doc-drift, index-currency,
  diagram-existence,
  or pre-merge simulation found problems

#### Scenario: Tooling-currency drift does not affect the workflow's outcome

- **GIVEN** the workflow-ref alignment check and the skills/tooling drift check
  both find drift
- **WHEN** the PR workflow's final gating step runs
- **THEN** the workflow's pass/fail outcome is unaffected by either finding

### Requirement: Separate provider workflows preserve the PR evaluation contract

The template SHALL ship independent LiteLLM and Bedrock reusable PR workflows.
Each SHALL own its provider
setup, authentication, dependency installation, preflight, canonical inputs and
secrets, and complete PR
evaluation job. Both workflows MUST preserve the existing initialization,
independent-check execution,
reporting, gating, simulation, and branch-push contracts. Provider-independent
merge and PR-close workflows
SHALL remain shared.

#### Scenario: LiteLLM PR evaluation

- **WHEN** a correctly wired LiteLLM child opens or updates a PR
- **THEN** the LiteLLM workflow runs the complete existing PR evaluation
  contract without AWS setup

#### Scenario: Bedrock PR evaluation

- **WHEN** a correctly wired Bedrock child opens or updates a PR
- **THEN** the Bedrock workflow obtains credentials through the selected trusted
  credential mode, installs
  its isolated dependency, preflights Converse, and then runs the same complete
  PR evaluation contract

### Requirement: Bedrock credential modes preserve the evaluation contract

The Bedrock reusable workflow SHALL obtain AWS credentials after checking out
the instance and before
provider preflight. In `github-oidc` mode, it SHALL configure the selected AWS
IAM role and region through
GitHub OIDC. In `instance-managed` mode, it SHALL invoke only the fixed
checked-out instance action at
`.github/actions/panopticon-aws-credentials/action.yml`, which SHALL set
temporary credentials and the
canonical Bedrock region environment. Both modes SHALL preserve the same
evaluation, reporting, gating,
and branch-push behavior.

#### Scenario: Instance-managed credentials run provider evaluation

- **WHEN** a Bedrock instance selects `instance-managed` and its fixed
  credential action succeeds
- **THEN** provider preflight and the subsequent PR evaluation use the
  credentials and region it supplied

#### Scenario: Credential action cannot be redirected

- **WHEN** a provider configuration contains a credential-action path override
- **THEN** the workflow rejects the invalid contract before invoking any action
  or LLM work

### Requirement: Legacy and stale callers fail with complete recovery instructions

The instance SHALL retain a legacy `panopticon-pr.yml` guard for callers
generated before provider
selection and each provider workflow SHALL validate its configuration revision
and canonical required
values before provider-dependent work. A legacy, stale, or empty renamed-secret
path SHALL fail as an
operational error with a concise annotation and a detailed step summary. When
configuration is required,
the summary SHALL state the cause, show the resolved instance's direct LiteLLM
and Bedrock configuration
workflow URLs, give ordered provider-choice console instructions and equivalent
`gh workflow run` commands
for both provider entrypoints, and give the exact one-line child bootstrap
command plus commit, push, and
rerun instructions when caller regeneration is required.

#### Scenario: Legacy generic caller runs against an unconfigured instance

- **WHEN** a child still references instance workflow `panopticon-pr.yml` and
  the resolved instance has no
  selected provider
- **THEN** the guard fails after reading the child instance identity and prints
  both provider-specific
  configuration paths plus complete child-bootstrap recovery commands rather
  than producing a workflow-load
  error

#### Scenario: Provider revision is stale

- **WHEN** a provider workflow receives a configuration revision different from
  the live instance contract
- **THEN** it fails before LLM checks and prints an exact installer command in
  the form
  `curl -fsSL <public-installer-url> | PANOPTICON_INSTANCE='<owner/repo>'
  python3`

### Requirement: Provider workflow failures have actionable summaries

Each provider-specific PR-evaluation workflow SHALL write the detected failure
reason and a corrective
action to the GitHub Actions step summary before any explicit non-zero exit
caused by invalid provider
configuration, a missing required credential action, or a failed branch-state
index merge. Its concise
workflow annotation SHALL direct the maintainer to the summary.

#### Scenario: Bedrock credential action is unavailable

- **GIVEN** the instance selects `instance-managed` Bedrock credentials
- **WHEN** the checked-out instance lacks
  `.github/actions/panopticon-aws-credentials/action.yml`
- **THEN** the Bedrock workflow exits non-zero before provider preflight and its
  step summary identifies
  the required action path and the available credential-mode recovery

#### Scenario: Branch-state merge fails

- **WHEN** either provider workflow cannot merge the PR branch state into the
  instance branch
- **THEN** it exits non-zero and its step summary identifies the failed merge,
  its exit status, and the
  instruction to correct the reported index or configuration problem before
  rerunning
