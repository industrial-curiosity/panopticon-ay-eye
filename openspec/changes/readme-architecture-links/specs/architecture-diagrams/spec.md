## ADDED Requirements

### Requirement: Child repo README links to both diagrams

A child repo's `README.md` SHALL contain, at the top of the file, two markdown links in this order: the
repo's own architecture diagram link directly above the org architecture diagram link. Both SHALL be labeled
with the repo name to distinguish them (`{repo} architecture` and `org architecture`), never a bare
"architecture" label. These are written by the `panopticon-doc-generation` skill as part of its normal
architecture-overview pass — the same agent-authored treatment as the existing `## Architecture diagram`
back-link — not a separate deterministic script or a standalone CI check.

The own-repo link SHALL be a relative markdown link to this repo's `architecture.md` at its configured
`docs_location` (e.g. `docs/architecture.md`), following the same relative-link discipline as the existing
diagram-section back-link: it resolves once this repo's docs are merged into the instance repo, not
necessarily before.

The org link SHALL be a fully-qualified GitHub URL, derived using the same inputs and fallback order as the
`org_diagram_link` script (`panopticon/config.json`'s `instance`, `instance_default_branch`, and `repo`
fields; a live `gh api` fallback when `instance_default_branch` is absent; a loud failure, never a guessed
branch name, when both are unavailable) — so it resolves immediately, without waiting for a merge.

#### Scenario: Doc generation writes both links in the correct order

- **GIVEN** a child repo with `panopticon/config.json` `repo: "svc-a"`, `instance:
  "acme/panopticon-instance"`, and `instance_default_branch: "main"`
- **WHEN** `panopticon-doc-generation` produces or refreshes `README.md`
- **THEN** the top of the file contains `[svc-a architecture](docs/architecture.md)` immediately followed by
  `[org architecture](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`, in
  that order

#### Scenario: Org link falls back to a live lookup when instance_default_branch is absent

- **GIVEN** a child repo's `panopticon/config.json` has `instance` and `repo` but no
  `instance_default_branch`, and `gh` is installed and authenticated
- **WHEN** `panopticon-doc-generation` writes the README org link
- **THEN** it resolves the instance's default branch live via `gh api` and writes the resulting URL, the same
  fallback behavior as the `org_diagram_link` script

#### Scenario: Missing config and failed live lookup fails loudly rather than guessing

- **GIVEN** a child repo's `panopticon/config.json` has no `instance_default_branch`, and `gh` is either not
  installed or not authenticated
- **WHEN** `panopticon-doc-generation` attempts to write the README org link
- **THEN** it stops and reports the gap rather than writing a link built from a guessed branch name

### Requirement: Instance repo README links to the org diagram only

An instance repo's `README.md` SHALL contain, at the top of the file, exactly one relative markdown link:
`[org architecture](docs/architecture.md)`. It SHALL NOT contain links to individual child repos' diagrams —
the org diagram itself already enumerates every repo with an external interface or dependency.

#### Scenario: Instance README contains only the org link

- **WHEN** an instance repo's `README.md` top matter is inspected
- **THEN** it contains `[org architecture](docs/architecture.md)` and no per-child-repo diagram links

### Requirement: Org diagram renders an explicit empty-state placeholder

When the compiled index (interfaces and dependencies combined) contains zero repo sections, `write_org_diagram`
SHALL write a placeholder `docs/architecture.md` rather than an empty or minimal document: a diagram depicting
six nodes labeled `?`, connected to form a hexagon with no meaningful edge labels, preceded by a markdown link
to `docs/setup-guide.md#4-initialize-a-child-repo`. This placeholder SHALL be produced by the same
deterministic render path every time `write_org_diagram` runs against a zero-repo compiled index — not written
once and left stale — so it stays current if the org config or diagram format changes before the first child
repo merges.

#### Scenario: write_org_diagram renders the placeholder for an empty compiled index

- **GIVEN** a compiled interface index and compiled dependency index that together contain zero repo sections
- **WHEN** `write_org_diagram` runs
- **THEN** it writes `docs/architecture.md` containing the link to `docs/setup-guide.md#4-initialize-a-child-repo`
  followed by a diagram of six `?`-labeled nodes forming a hexagon

#### Scenario: First real merge replaces the placeholder

- **GIVEN** an instance repo whose `docs/architecture.md` is currently the empty-state placeholder
- **WHEN** the first child repo merges an interface or dependency that produces at least one repo section
- **THEN** `write_org_diagram` overwrites the placeholder with the real org diagram content

### Requirement: Template repo ships a non-dead placeholder and instance-appropriate README seed

The template repo SHALL ship the empty-state placeholder `docs/architecture.md` (see "Org diagram renders an
explicit empty-state placeholder") directly in its tracked tree, so a newly created instance repo's
`README.md` org-architecture link is never dead, even before any `write_org_diagram` run.

The template repo's own `README.md` Overview section (the paragraph between the `## Overview` heading and the
logo image) SHALL be org-agnostic instance-appropriate boilerplate plus the `[org architecture]
(docs/architecture.md)` link, followed by a maintainer note — placed between that text and the logo image —
instructing the org to replace the paragraph with a description specific to their organization. No dynamic
substitution of org-specific content SHALL be assumed or attempted, since no reliable event fires when a
repository is created from a template.

#### Scenario: Fresh instance repo has a working architecture link on day one

- **GIVEN** an organization creates a new instance repo via "Use this template"
- **WHEN** they open the newly created repo's `README.md` before running any Panopticon tooling
- **THEN** the `[org architecture](docs/architecture.md)` link resolves to the shipped placeholder content,
  not a broken link

#### Scenario: Maintainer note appears between the overview text and the logo

- **WHEN** the template repo's `README.md` is inspected
- **THEN** the Overview section reads: instance-appropriate boilerplate text, then the org architecture link,
  then a maintainer note instructing the org to personalize the paragraph, then the logo image — in that
  order
