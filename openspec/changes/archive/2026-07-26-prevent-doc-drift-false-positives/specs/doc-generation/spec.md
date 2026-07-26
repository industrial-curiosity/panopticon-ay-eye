## MODIFIED Requirements

### Requirement: Doc-vs-code drift detection

The tooling SHALL provide an LLM-based drift check that, given a PR's
behavior-bearing code or configuration changes and the current docs, judges
whether documentation updates are required. Developers keep their repo's docs
and index up to date locally with their own agents, and CI verifies that they
have. Documentation-only, agent-skill, OpenSpec, changelog, and test-only diffs
SHALL produce a clean doc-drift verdict without an LLM call.

This judgment SHALL cover the architecture overview's diagram section the same
as its prose: a diagram that no longer reflects the code's components or
relationships is stale, judged and reported the same way as stale prose. A
changed document that already covers the relevant behavior SHALL not be reported
as stale.

Every stale reason SHALL identify a changed behavior-bearing file that supports
the claimed documentation gap, name one documentation file, explain the gap,
and state a non-empty update needed to resolve it. A contradictory, empty, or
untraceable stale reason SHALL be treated as an operational failure rather than
an actionable stale-doc verdict.

When docs are stale the check SHALL fail loudly and clearly, and the GitHub
Actions step summary SHALL contain concrete, actionable remediation
instructions: for each stale doc, which doc it is, why it is stale, and the
exact command or skill that fixes it (`panopticon-doc-generation`, or the
specific `python3 -m panopticon.docs` command for interface docs). The summary
SHALL also state, in plain terms, that the fix must be committed and pushed to
this same PR's branch — not a new PR — and that the check re-runs automatically
on that push. Org gating configuration MAY downgrade the check to advisory.

#### Scenario: Code change affecting documented behavior

- **WHEN** a PR changes a component's public behavior without touching its docs
- **THEN** the drift check fails with a stale reason tied to the changed
  behavior-bearing file, and both the GitHub Actions summary and the PR comment
  name which docs are stale, why, the exact regeneration command or skill for
  each, and that pushing the fix to this branch re-triggers the check

#### Scenario: Docs updated alongside code

- **WHEN** a PR updates docs consistently with its code changes
- **THEN** the drift check passes and says so in the CI summary

#### Scenario: Documentation-generation guidance and its generated document change together

- **WHEN** a PR changes documentation-generation guidance and updates the
  affected child architecture document to match, without a behavior-bearing
  code or configuration change
- **THEN** the drift check returns a clean verdict without calling the LLM

#### Scenario: Contradictory stale reason is an operational failure

- **WHEN** the LLM returns a stale reason whose required update is empty, says
  no update is needed, or cannot identify a changed behavior-bearing file
- **THEN** the drift check does not emit a stale-doc verdict and instead exits
  through its operational-failure path with an explanation of the invalid
  response

#### Scenario: Remediation instructions are self-contained

- **GIVEN** a developer who has never seen a Panopticon doc-drift failure before
- **WHEN** they read only the GitHub Actions step summary, with no other context
- **THEN** they can tell exactly which doc(s) to fix, why, and the precise steps
  to resolve and re-trigger the check, without needing to consult any
  documentation outside the summary itself

#### Scenario: Diagram no longer reflects the code

- **WHEN** a PR changes a repo's components or their relationships in a way the
  `## Architecture diagram` section no longer reflects, without updating that
  section
- **THEN** the drift check fails, naming the architecture overview's diagram
  section as stale, why, and that running `panopticon-doc-generation` resolves
  it
