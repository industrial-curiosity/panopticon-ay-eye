# Doc Generation Spec

## Requirements

### Requirement: Four documentation layers

Doc generation SHALL produce four layers per repo: an architecture overview
(purpose, components, data flow,
dependencies, and an architecture diagram section per the architecture-diagrams
capability), per-component
docs following a fixed template, interface docs, and operational docs (how to
run/deploy/test, required
configuration). Generated docs SHALL live in the repo's configured documentation
location (adopted or chosen
at initialization and recorded in `panopticon/config.json`) so the sync workflow
can copy them to
`docs/{repo}/` in the instance repo. Generation and doc updating SHALL be
defined as harness-portable agent
skills, so that local runs execute in the user's preferred AI agent harness with
no Panopticon LLM
configuration.

#### Scenario: Local doc update through the user's harness

- **WHEN** a user updates a repo's docs locally using the bundled skills in
  their own agent harness
- **THEN** the four-layer structure and templates are honored without
  `PANOPTICON_LLM_*` configuration

#### Scenario: Initial generation

- **WHEN** doc generation runs on a repo during initialization
- **THEN** all four layers exist in the repo's docs location, each following its
  template, and the
  architecture overview includes the `## Architecture diagram` section

### Requirement: Interface docs rendered from the index

Interface docs SHALL be a human-readable rendering of the repo's local interface
index (deterministic
rendering, not LLM prose), so that interface docs can never disagree with the
index.

#### Scenario: Index and interface docs stay consistent

- **WHEN** the local index changes and docs are regenerated
- **THEN** the interface docs reflect exactly the entries in the updated index

### Requirement: Doc-vs-code drift detection

The tooling SHALL provide an LLM-based drift check that, given a PR's
code/configuration changes and the
current docs, judges whether documentation updates are required — developers
keep their repo's docs and index
up to date locally with their own agents, and CI verifies that they have. This
judgment SHALL cover the
architecture overview's diagram section the same as its prose: a diagram that no
longer reflects the code's
components or their relationships is stale, judged and reported the same way as
stale prose. When docs are
stale the check SHALL fail loudly and clearly, and the GitHub Actions step
summary SHALL contain concrete,
actionable remediation instructions, not just a description of the problem: for
each stale doc, which doc it
is, why it's stale, and the exact command or skill that fixes it
(`panopticon-doc-generation`, or the specific
`python3 -m panopticon.docs` command for interface docs). The summary SHALL also
state, in plain terms, that
the fix must be committed and pushed to this same PR's branch — not a new PR —
and that the check re-runs
automatically on that push. Org gating configuration MAY downgrade the check to
advisory.

#### Scenario: Code change affecting documented behavior

- **WHEN** a PR changes a component's public behavior without touching its docs
- **THEN** the drift check fails, and both the GitHub Actions summary and the PR
  comment name which docs are
  stale, why, the exact regeneration command or skill for each, and that pushing
  the fix to this branch
  re-triggers the check

#### Scenario: Docs updated alongside code

- **WHEN** a PR updates docs consistently with its code changes
- **THEN** the drift check passes and says so in the CI summary

#### Scenario: Remediation instructions are self-contained

- **GIVEN** a developer who has never seen a Panopticon doc-drift failure before
- **WHEN** they read only the GitHub Actions step summary, with no other context
- **THEN** they can tell exactly which doc(s) to fix, why, and the precise steps
  to resolve and re-trigger
  the check, without needing to consult any documentation outside the summary
  itself

#### Scenario: Diagram no longer reflects the code

- **WHEN** a PR changes a repo's components or their relationships in a way the
  `## Architecture diagram`
  section no longer reflects, without updating that section
- **THEN** the drift check fails, naming the architecture overview's diagram
  section as stale, why, and that
  running `panopticon-doc-generation` resolves it

### Requirement: Regeneration updates in place

Doc regeneration SHALL update the existing generated docs in place, preserving
the layer structure, and MUST
NOT create parallel copies or leave stale sections for removed components.

#### Scenario: Component removed from codebase

- **WHEN** docs are regenerated after a component is deleted
- **THEN** that component's per-component doc is removed and references to it
  are gone from the overview

### Requirement: Initialization-time drift resolution

During initialization (interface naming, interface extraction, and doc
generation — all run locally via the
user's own agent harness, with full repo context and write access), when the
tooling discovers that existing
repository documentation contradicts the actual current state of the repository
— describing code,
configuration, or interfaces that have since changed, been removed, or were
never actually implemented as
documented — it SHALL resolve the contradiction by revising the affected
documentation to match the current
repo state, rather than pausing on every such mismatch. The revised
documentation's prose SHALL NOT call out
the resolution inline. Instead, each resolved contradiction SHALL be recorded as
an entry appended to a
Panopticon changelog file (`panopticon-changelog.md`, in the repo's configured
documentation location)
naming the doc, what was found, and how it was resolved — visible to maintainers
without cluttering the
generated docs themselves. The changelog file is an ordinary generated artifact:
Panopticon SHALL NOT stage,
commit, or push it automatically; whether to keep, edit, or discard it is the
user's call at their own
commit step, same as every other file initialization produces. When the correct
resolution is ambiguous —
intent cannot be determined from the repo alone, such as work that was planned
but never finished, or
genuinely conflicting signals — the tooling SHALL stop and prompt the user for
intervention rather than
guessing.

This is distinct from the "Doc-vs-code drift detection" requirement: that check
runs on PR diffs in CI and
only reports a verdict, never editing docs, because CI has no mandate to
silently rewrite a developer's
documentation. This requirement governs the local, agent-driven initialization
flow only, which has full
repo context and write access and can actually repair drift it discovers rather
than only flag it.

#### Scenario: Doc describes a component that no longer matches the code

- **GIVEN** a repo's existing documentation describes an interface or component
  whose actual implementation
  has since diverged (renamed, removed, or restructured)
- **WHEN** initialization runs and this mismatch is discovered
- **THEN** the documentation is revised to match the current code with no inline
  callout, and a new entry
  describing the mismatch and its resolution is appended to
  `panopticon-changelog.md` in the docs location

#### Scenario: Documented interface was never actually implemented

- **GIVEN** a repo's documentation describes an interface backed by source files
  that don't exist anywhere in
  the repo, with nothing else in the repo clarifying whether the work is still
  pending
- **WHEN** initialization runs and finds no source-file evidence for that
  interface
- **THEN** the tooling stops and prompts the user for how to proceed, rather
  than fabricating the missing
  interface or silently dropping it from the docs

#### Scenario: Ambiguous resolution prompts the user

- **GIVEN** documentation drift where the correct resolution cannot be
  determined solely from the repo's
  current state
- **WHEN** initialization encounters this drift
- **THEN** it presents the ambiguity to the user with the available options and
  does not proceed until the
  user decides

#### Scenario: Changelog is left for the user to commit or discard

- **GIVEN** initialization has resolved one or more documentation contradictions
  and appended entries to
  `panopticon-changelog.md`
- **WHEN** initialization finishes
- **THEN** the changelog file exists in the docs location as an ordinary
  uncommitted file — Panopticon SHALL
  NOT stage, commit, or push it — and the user decides whether to keep, edit, or
  discard it at their own
  commit step
