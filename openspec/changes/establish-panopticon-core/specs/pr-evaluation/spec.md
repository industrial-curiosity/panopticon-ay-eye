## ADDED Requirements

### Requirement: Initialization check

The PR workflow SHALL verify that the repo is Panopticon-initialized (`panopticon/config.json` present); when
it is not, the check SHALL fail with an actionable message pointing at the init procedure.

#### Scenario: Uninitialized repo

- **WHEN** a PR runs in a repo without `panopticon/config.json`
- **THEN** the check fails, reporting that the repo is not initialized and how to initialize it, and remaining
  Panopticon checks are skipped

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
because LLM-extracted entries can produce false positives. The instance repo's `panopticon.config.json` SHALL
allow orgs to adjust each check type (init, doc-drift, interface-conflict) between advisory and blocking.
Workflows MUST read gating configuration rather than hardcoding outcomes.

#### Scenario: Interface conflicts advisory by default

- **WHEN** a conflict is detected and the org has not changed gating configuration
- **THEN** the check reports the conflict but the workflow succeeds

#### Scenario: Stale docs fail by default

- **WHEN** the drift check finds stale docs and the org has not changed gating configuration
- **THEN** the workflow fails with the drift report

#### Scenario: Org escalates conflicts to blocking

- **WHEN** `panopticon.config.json` marks interface-conflict checks as blocking and a conflict is detected
- **THEN** the check fails so branch protection can block the merge

### Requirement: Combined report leads with a de-duplicated action list

The PR workflow's combined report — the GitHub Actions step summary and the PR comment, both built from the
same doc-drift, index-currency, and pre-merge-simulation findings — SHALL open with a "TL;DR" section listing
the concrete actions a developer must take to resolve everything the checks found, before any per-check
detail. Every doc-drift and index-currency finding SHALL collapse into a single TL;DR action — regardless of
how many docs are stale or whether the index itself is also stale — instructing the developer to run the
panopticon-doc-generation skill once, since that skill's own rules already keep the index current before
regenerating every stale doc in the same pass; the TL;DR MUST NOT list a separate line per stale doc or a
separate line for the index update. Interface conflicts from pre-merge simulation are a distinct concern —
resolving cross-repo ownership/naming, not something a single doc-generation pass fixes — and remain their
own action(s), never folded into the doc-generation line. The same TL;DR SHALL be repeated verbatim at the
end of the report, after the per-check detail, so it's visible whether a reader scans from the top or
scrolls to the bottom. When every check passes, the TL;DR SHALL say so plainly instead of listing actions.

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

- **GIVEN** doc-drift, index-currency, and pre-merge simulation all pass
- **WHEN** the combined report is generated
- **THEN** the TL;DR states plainly that everything passed, with no action items, at both the top and bottom
  of the report

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
