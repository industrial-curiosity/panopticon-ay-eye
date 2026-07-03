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
