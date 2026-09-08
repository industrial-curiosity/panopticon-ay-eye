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
timeout for its evaluate job from the canonical workflow input mapped by child
bootstrap from the configured organization-level job-timeout variable name,
using 20 minutes when the mapped value is unset. The setup guide SHALL
document that the value accepts a whole number from 10 through 60 and is
evaluated by GitHub Actions before the job starts. Instance configuration and
the fixed instance default-resolver action SHALL NOT supply this job-level
value, and changing the organization variable or workflow fallback SHALL NOT
require child-repository maintainer action.

#### Scenario: Default evaluate-job duration

- **WHEN** a provider-specific PR workflow receives no mapped job-timeout value
- **THEN** GitHub Actions terminates the evaluate job after 20 minutes if it has
  not completed

#### Scenario: Instance administrators change the evaluate-job duration

- **GIVEN** an instance administrator changes the mapped organization Actions
  variable to a whole number from 10 through 60
- **WHEN** a child repository invokes the reusable workflow
- **THEN** the selected provider workflow uses that number without requiring
  child caller regeneration or a child maintainer commit

#### Scenario: Legacy instance default is not a live timeout source

- **GIVEN** an existing instance configuration contains a legacy
  `job_timeout_minutes` default
- **WHEN** the provider workflow starts
- **THEN** it ignores that legacy value and uses the organization variable or
  the reusable-workflow fallback

### Requirement: Provider workflows resolve effective configuration before preflight

Each provider-specific reusable PR workflow SHALL resolve optional non-secret
provider inputs through the validated contract before provider preflight and
LLM work. It SHALL invoke only the fixed checked-out instance
`.github/actions/panopticon-provider-defaults/action.yml` when an action output
is needed, and SHALL not allow instance configuration or a child caller to
choose another action path. The workflow SHALL preserve raw caller inputs until
resolution so a template workflow default cannot mask a higher-precedence
source. It SHALL expose only source labels in its summary and environment
diagnostics, never a resolved value or credential.

The workflow SHALL receive `job_timeout_minutes` already resolved by the
generated caller. It SHALL NOT attempt to obtain that job-level value from the
fixed instance action because GitHub evaluates job timeout before job steps run.

#### Scenario: Workflow uses a template default only after higher sources are absent

- **GIVEN** an optional input is absent from organization Actions, the fixed
  instance action, and instance configuration but has a declared workflow
  default
- **WHEN** the reusable workflow resolves effective configuration
- **THEN** it uses the workflow default and records `workflow default` as the
  source before provider preflight

#### Scenario: Required input cannot be supplied by a default

- **GIVEN** a required provider input is absent from the child caller
- **WHEN** the reusable workflow starts
- **THEN** it fails before invoking the default-resolver action or provider
  preflight and identifies the required logical name and configuration path

#### Scenario: Job timeout is resolved before the workflow starts

- **GIVEN** an instance configuration supplies a valid non-secret job-timeout
  default and the organization Actions variable is absent
- **WHEN** the generated caller invokes the reusable workflow
- **THEN** the workflow uses the caller-supplied timeout and does not invoke the
  fixed instance action to resolve it

#### Scenario: Fixed default action output is invalid

- **GIVEN** an optional value requires the fixed instance action and the action
  is missing, returns an undeclared output, or returns an empty value
- **WHEN** the reusable workflow resolves effective configuration
- **THEN** it fails before provider preflight and its step summary names the
  fixed path, logical value, and recovery action without printing a value

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

### Requirement: Planned doc-drift batching SHALL preserve independent PR evaluation

The PR workflow SHALL treat a doc-drift planning or batch-evaluation failure as
the existing doc-drift operational failure. It SHALL continue to run
index-currency and pre-merge simulation, include each check's actual status in
the combined report, and apply the existing final-gate policy after all
independent checks complete.

#### Scenario: Doc-drift batch evaluation times out

- **WHEN** doc drift reports a timed-out evaluation batch
- **THEN** index-currency and pre-merge simulation still run and the final gate
  fails with the doc-drift operational-failure annotation

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

### Requirement: Doc-drift context is relevance-first and conservative

For a behavior-bearing pull-request diff, doc drift SHALL exclude the
deterministically rendered `interfaces.md` document from LLM context. It SHALL
include `architecture.md` and `operations.md`. It SHALL include a component
document when that document explicitly names a behavior-bearing changed path.
If any behavior-bearing changed path has no deterministic component-document
match, doc drift SHALL include every component document that fits within its
existing bounded input budget. The check report SHALL state the context-
selection mode and selected documentation paths.

#### Scenario: Changed path is explicitly documented by one component

- **GIVEN** a behavior-bearing changed path is explicitly named by one
  component document
- **WHEN** doc drift prepares its LLM context
- **THEN** it includes architecture, operations, and that component document,
  excludes deterministic interfaces, and reports targeted component context

#### Scenario: Changed path has no deterministic component-document match

- **GIVEN** at least one changed behavior path is not explicitly named by any
  component document
- **WHEN** doc drift prepares its LLM context
- **THEN** it includes architecture, operations, and every component document
  within the existing byte budget and reports conservative fallback

#### Scenario: No behavior-bearing change

- **WHEN** a PR changes no behavior-bearing path
- **THEN** doc drift returns its clean deterministic verdict without creating
  an LLM request or request diagnostics

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
response, a missing or unreachable endpoint, or any other exception raised
while producing the verdict — SHALL be caught explicitly and turned into a
non-`0`/non-`2` exit paired with a clear plain-text diagnostic and an
operational-failure report section. The check CLI and its wrapper step SHALL
NOT emit GitHub `::error::` workflow commands for that failure. After all
independent checks and the combined report have run, the final gating step
SHALL emit exactly one Panopticon-authored `::error::` annotation for each
operationally failed check and fail the workflow.

#### Scenario: Malformed LLM response is an operational failure, not a stale verdict

- **GIVEN** the LLM endpoint returns a response that fails to parse as the
  expected verdict JSON
- **WHEN** the doc-drift or index-currency check runs
- **THEN** the check exits with a code that is neither `0` nor `2`, writes an
  operational-failure report rather than a real stale finding, and the final
  gate emits one Panopticon-authored `::error::` annotation identifying the
  failed check

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

The template SHALL ship independent LiteLLM, OpenAI, and Bedrock reusable PR workflows.
Each SHALL own its provider
setup, authentication, dependency installation, preflight, canonical inputs and
secrets, and complete PR
evaluation job. All workflows MUST preserve the existing initialization,
independent-check execution,
reporting, gating, simulation, and branch-push contracts. Provider-independent
merge and PR-close workflows
SHALL remain shared. The OpenAI workflow SHALL be a correctly named clone of
the LiteLLM workflow's behavior, SHALL fix `PANOPTICON_LLM_PROVIDER` to `openai`,
and SHALL use OpenAI labels in its workflow name, summaries, and errors.

#### Scenario: OpenAI child evaluates a pull request

- **WHEN** an initialized child caller selects the OpenAI provider and supplies
  its configured key, model, instance token, and budget values
- **THEN** the OpenAI reusable workflow runs every configured PR check and
  applies the same configured gate outcomes as the LiteLLM reusable workflow
  using the fixed `https://api.openai.com/v1` endpoint

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

### Requirement: Provider workflow caller contracts are checked before release

The template SHALL test the declared `workflow_call` input and secret contract
of each provider-specific reusable PR-evaluation workflow against its GitHub
expression references before release. A workflow that references an undeclared
caller input or secret SHALL fail deterministic repository validation rather
than relying on GitHub Actions to reject a caller with zero jobs.

#### Scenario: Provider workflow contract validation succeeds

- **WHEN** the repository validation suite examines every shipped
  provider-specific reusable PR-evaluation workflow
- **THEN** each workflow has declarations for every referenced caller input and
  secret, and the validation succeeds

#### Scenario: Provider workflow contract validation detects a startup defect

- **WHEN** a provider-specific reusable PR-evaluation workflow introduces a
  reference to an undeclared caller input or secret
- **THEN** repository validation fails and identifies the undeclared reference

### Requirement: Bedrock credential modes preserve the evaluation contract

The Bedrock reusable workflow SHALL obtain AWS credentials after checking out
the instance and before provider preflight. In `github-oidc` mode, it SHALL
configure the selected AWS IAM role and region through GitHub OIDC. In
`instance-managed` mode, it SHALL invoke only the fixed checked-out instance
action at `.github/actions/panopticon-aws-credentials/action.yml`, SHALL bound
that action at the calling workflow-step boundary where GitHub Actions supports
the bound, and SHALL run a later caller-owned recovery step when the action
fails or times out. The recovery step SHALL run under an `always()`-style
condition, remain outside the composite action, identify the caller identity
and fixed action resource expected, and preserve the same evaluation,
reporting, gating, and branch-push behavior after successful credentials.

#### Scenario: Instance-managed credentials run provider evaluation

- **WHEN** a Bedrock instance selects `instance-managed` and its fixed
  credential action succeeds
- **THEN** provider preflight and the subsequent PR evaluation use the
  credentials and region it supplied, and the caller-owned recovery step is
  silent because the credential step outcome is successful

#### Scenario: Credential action fails or times out

- **WHEN** the fixed instance-managed credential action returns failure or is
  terminated by its caller-step timeout
- **THEN** a later `always()`-guarded caller step writes a gate-specific summary
  naming `.github/actions/panopticon-aws-credentials/action.yml`, the child
  caller repository, the instance/child ownership boundary, the exact identity
  registration recovery, and the rerun proof, then exits non-zero

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
reason and a corrective action to the GitHub Actions step summary before any
explicit non-zero exit caused by invalid provider configuration, a missing or
timed-out credential action, missing caller identity, or a failed branch-state
index merge. Its concise workflow annotation SHALL direct the maintainer to
the summary and SHALL be emitted on stdout so GitHub Actions creates the
annotation. The summary SHALL identify the failed gate, expected configured
name or resource, whether the repair is instance-wide or per child, where to
fix it, and how to rerun.

#### Scenario: Caller identity is unavailable

- **WHEN** the credential setup succeeds but the caller's cloud identity
  cannot be verified
- **THEN** the workflow fails before provider preflight with a gate-3 summary
  naming the child caller, the configured credential mode/resource, the
  per-child identity owner, and the exact registration or caller-regeneration
  action

#### Scenario: Bedrock credential action is unavailable

- **GIVEN** the instance selects `instance-managed` Bedrock credentials
- **WHEN** the checked-out instance lacks
  `.github/actions/panopticon-aws-credentials/action.yml`
- **THEN** the Bedrock workflow emits its annotation on stdout, exits non-zero
  before provider preflight, and its step summary identifies the required
  action path and the available credential-mode recovery

#### Scenario: Branch-state merge fails

- **WHEN** either provider workflow cannot merge the PR branch state into the
  instance branch
- **THEN** it exits non-zero and its step summary identifies the failed merge,
  its exit status, the affected instance resource, and the instruction to
  correct the reported index or configuration problem before rerunning

### Requirement: PR evaluation explains instance-index candidate matches

The PR workflow SHALL prepare a bounded, relevant set of instance interface
candidates for each changed or proposed child interface after downloading the
instance compiled index and before publishing its combined report. The CI LLM
SHALL classify each candidate as likely same interface, likely distinct
interface, or insufficient evidence, and cite available child and instance
evidence. This analysis SHALL be advisory and SHALL not mutate hints, the local
index, the deterministic simulation result, or gate state.

#### Scenario: Semantic near-match is surfaced without automatic merge

- **WHEN** the proposed child index has an interface that resembles an instance
  entry but deterministic simulation finds no exact conflict
- **THEN** the PR report prominently identifies the candidate and its evidence
  as advisory follow-up without changing either index

### Requirement: PR report visualizes prospective child architecture

The maintained Panopticon PR report comment SHALL include the validated Mermaid
block from the child architecture overview, the deterministic prospective-merge
result, and the instance-index candidate analysis. The workflow SHALL update
its marker-owned comment instead of overwriting the PR author's description.

#### Scenario: Report includes a valid architecture diagram

- **WHEN** a child PR has a valid Mermaid architecture diagram
- **THEN** the maintained Panopticon report comment renders that Mermaid block
  beneath a prospective-architecture heading with the merge findings

#### Scenario: Diagram is unavailable

- **WHEN** the child diagram is missing or malformed
- **THEN** the report explicitly identifies the unavailable diagram and retains
  the existing diagram-check outcome without fabricating a replacement diagram

### Requirement: Child conflict-gating override takes precedence

The PR workflow SHALL determine the effective `interface-conflict` gating mode
by reading a valid child-repository `panopticon/config.json` override first,
then the instance repository's `panopticon.config.json` value, then the built-in
`advisory` default. Both advisory and blocking outcomes SHALL publish the same
prominent conflict warning and effective-policy explanation. Only the blocking
outcome SHALL fail the conflict check.

#### Scenario: Child retains advisory mode against a blocking instance default

- **WHEN** the instance config marks `interface-conflict` as `blocking` and the
  child config explicitly marks it `advisory`
- **THEN** the PR reports the conflict and the child override prominently, but
  the conflict check succeeds

#### Scenario: Child escalates an advisory instance default

- **WHEN** the instance config is advisory and the child config marks
  `interface-conflict` as `blocking`
- **THEN** a detected deterministic conflict produces the prominent warning and
  fails the conflict check

### Requirement: Missing instance-managed credential recovery is copyable

The Bedrock provider workflow SHALL identify the fixed credential-action path,
link the public credential-action example, show a copyable `protected_paths`
fragment for other custom instance files, and provide the child-bootstrap
rerun command when the instance-managed action fails. The recovery SHALL state
that valid Bedrock `instance-managed` configuration protects the fixed path
automatically during template sync and SHALL never request or print credential
values.

#### Scenario: Fixed action is absent

- **WHEN** a Bedrock `instance-managed` run cannot find the fixed action
- **THEN** the step summary provides the example link, exact destination path,
  protection guidance, and child-bootstrap command

#### Scenario: Shared recovery formatter cannot be imported

- **WHEN** caller-side failure reporting runs before the shared formatter is
  importable
- **THEN** the inline fallback contains the same path, example, protection,
  and rerun guidance

### Requirement: Reusable PR workflows expose only consumed caller inputs

Each provider-specific reusable PR-evaluation workflow SHALL omit
`configuration_defaults` from its `workflow_call` contract, and generated PR
callers SHALL NOT pass that input, because timeout resolution is owned by the
organization variable and reusable-workflow fallback.

#### Scenario: Generated caller invokes a provider workflow

- **WHEN** bootstrap renders the provider PR caller
- **THEN** the caller and the selected reusable workflow contain no
  `configuration_defaults` input declaration or mapping

### Requirement: Feature-mode PR evaluation

Each provider-specific reusable PR workflow SHALL load the effective instance
feature modes from its checked-out instance configuration and run feature checks
through fixed conditional steps or fixed environment flags. It SHALL not add a
feature-specific caller input, secret mapping, or selectable workflow path.
Disabled checks SHALL be skipped, advisory checks SHALL report without failing
the workflow, and blocking checks SHALL contribute their validated failure to
the existing final gating outcome.

#### Scenario: Blocking OKF check fails a PR

- **WHEN** the instance enables OKF in blocking mode and a child documentation
  bundle fails OKF validation
- **THEN** the shared PR workflow reports the violation and fails through its
  normal final gating outcome

#### Scenario: Disabled OKF check does not run

- **WHEN** the instance disables OKF
- **THEN** the shared PR workflow does not invoke OKF validation or require OKF
  feature artifacts in the child

### Requirement: Pinned workflow summary warning

The shared PR workflow SHALL compare the child caller's actual reusable
workflow ref with the instance configuration's `workflow_ref`. When the refs
differ, the first section of its step summary SHALL be a non-blocking caution
warning naming the child's pinned ref, the instance's configured current ref,
and the exact bootstrap or sync action that refreshes the child. It SHALL not
infer a latest tag and SHALL not fail the workflow solely because of this
warning.

#### Scenario: Child caller uses a stale pinned ref

- **WHEN** a child caller uses a tag, branch, or commit SHA different from the
  instance's configured `workflow_ref`
- **THEN** the summary begins with a caution warning that names both refs and
  remains non-blocking
