## MODIFIED Requirements

### Requirement: Four documentation layers

Doc generation SHALL produce four layers per repo: an architecture overview (purpose, components, data flow,
dependencies, and an architecture diagram section per the architecture-diagrams capability), per-component
docs following a fixed template, interface docs, and operational docs (how to run/deploy/test, required
configuration). Generated docs SHALL live in the repo's configured documentation location (adopted or chosen
at initialization and recorded in `panopticon/config.json`) so the sync workflow can copy them to
`docs/{repo}/` in the instance repo. Generation and doc updating SHALL be defined as harness-portable agent
skills, so that local runs execute in the user's preferred AI agent harness with no Panopticon LLM
configuration.

#### Scenario: Local doc update through the user's harness

- **WHEN** a user updates a repo's docs locally using the bundled skills in their own agent harness
- **THEN** the four-layer structure and templates are honored without `PANOPTICON_LLM_*` configuration

#### Scenario: Initial generation

- **WHEN** doc generation runs on a repo during initialization
- **THEN** all four layers exist in the repo's docs location, each following its template, and the
  architecture overview includes the `## Architecture diagram` section

### Requirement: Doc-vs-code drift detection

The tooling SHALL provide an LLM-based drift check that, given a PR's code/configuration changes and the
current docs, judges whether documentation updates are required — developers keep their repo's docs and index
up to date locally with their own agents, and CI verifies that they have. This judgment SHALL cover the
architecture overview's diagram section the same as its prose: a diagram that no longer reflects the code's
components or their relationships is stale, judged and reported the same way as stale prose. When docs are
stale the check SHALL fail loudly and clearly, and the GitHub Actions step summary SHALL contain concrete,
actionable remediation instructions, not just a description of the problem: for each stale doc, which doc it
is, why it's stale, and the exact command or skill that fixes it (`panopticon-doc-generation`, or the specific
`python3 -m panopticon.docs` command for interface docs). The summary SHALL also state, in plain terms, that
the fix must be committed and pushed to this same PR's branch — not a new PR — and that the check re-runs
automatically on that push. Org gating configuration MAY downgrade the check to advisory.

#### Scenario: Code change affecting documented behavior

- **WHEN** a PR changes a component's public behavior without touching its docs
- **THEN** the drift check fails, and both the GitHub Actions summary and the PR comment name which docs are
  stale, why, the exact regeneration command or skill for each, and that pushing the fix to this branch
  re-triggers the check

#### Scenario: Docs updated alongside code

- **WHEN** a PR updates docs consistently with its code changes
- **THEN** the drift check passes and says so in the CI summary

#### Scenario: Remediation instructions are self-contained

- **GIVEN** a developer who has never seen a Panopticon doc-drift failure before
- **WHEN** they read only the GitHub Actions step summary, with no other context
- **THEN** they can tell exactly which doc(s) to fix, why, and the precise steps to resolve and re-trigger
  the check, without needing to consult any documentation outside the summary itself

#### Scenario: Diagram no longer reflects the code

- **WHEN** a PR changes a repo's components or their relationships in a way the `## Architecture diagram`
  section no longer reflects, without updating that section
- **THEN** the drift check fails, naming the architecture overview's diagram section as stale, why, and that
  running `panopticon-doc-generation` resolves it
