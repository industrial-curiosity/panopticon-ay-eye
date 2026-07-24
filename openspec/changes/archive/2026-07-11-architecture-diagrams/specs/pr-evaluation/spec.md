# Pr Evaluation Spec

## ADDED Requirements

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

## MODIFIED Requirements

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
