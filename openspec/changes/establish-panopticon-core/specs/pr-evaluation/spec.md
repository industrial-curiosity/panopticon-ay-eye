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
