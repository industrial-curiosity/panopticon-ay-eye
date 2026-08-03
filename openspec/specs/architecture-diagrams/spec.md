# Architecture Diagrams Specification

## Purpose

Define how Panopticon generates, links, configures, and synchronizes repository
and organization diagrams.

## Requirements

### Requirement: Diagram format configuration

Diagram rendering format SHALL be configurable per instance repo via
`panopticon.diagram.config.json` at the
instance repo root, with `format` defaulting to `mermaid` when the file is
absent. This configuration SHALL
NOT be overwritten by the `sync-from-template` workflow's merge (see the
repo-initialization capability's
protected-config mechanism). Child repos and CI checks SHALL read the effective
format from the instance
repo's checked-out configuration rather than assuming a hardcoded value.

#### Scenario: Default format with no config file

- **WHEN** an instance repo has no `panopticon.diagram.config.json`
- **THEN** the effective diagram format is `mermaid`

#### Scenario: Instance overrides the format

- **WHEN** an instance repo's `panopticon.diagram.config.json` sets an explicit
  `format` value
- **THEN** doc generation, the diagram-existence check, and org diagram
  rendering all use that configured
  format consistently

#### Scenario: Unsupported format fails loudly

- **WHEN** `panopticon.diagram.config.json` names a format with no implemented
  renderer
- **THEN** the diagram-existence check and the org-diagram rebuild both fail
  with an explicit "unknown
  diagram format" error rather than silently skipping diagram generation

### Requirement: Per-repo diagram section

Each repo's `architecture.md` SHALL contain a `## Architecture diagram` section
directly under which is
exactly one fenced code block tagged with the configured format's language
identifier, depicting the repo's
components and their relationships. This section is part of the
architecture-overview documentation layer
(doc-generation capability) and SHALL be agent-drawn and grounded in the actual
code, following the same
rules as the rest of that layer. Directly below the diagram, it SHALL include
proper markdown links to the repository's organization-diagram anchor and to
`operations.md#panopticon-analysis-scope`.

#### Scenario: Diagram section present after doc generation

- **WHEN** doc generation produces or updates `architecture.md`
- **THEN** the file contains a `## Architecture diagram` section with one fenced
  code block in the configured
  format depicting this repo's components and their relationships

#### Scenario: Diagram links back to the org diagram

- **WHEN** doc generation produces the `## Architecture diagram` section
- **THEN** the section includes a proper markdown link (not a bare URL) to the
  org diagram's anchor for
  this repo, built exactly as specified in "Diagram navigation uses plain links,
  not in-diagram
  click-through"

#### Scenario: Diagram links to analysis scope

- **WHEN** doc generation produces the `## Architecture diagram` section
- **THEN** directly below the diagram it includes a proper relative markdown
  link to `operations.md#panopticon-analysis-scope`

### Requirement: Org diagram document shape

The org diagram document SHALL be rendered deterministically from the compiled
index by the master-sync capability. It SHALL be a single document at the
instance repo root containing one section per repo that participates in at least
one interface or in at least one external dependency, ordered alphabetically by
repo name. Each section SHALL contain a relationship diagram and a table listing
every interface in which that repo participates, including an interface used or
managed by that repo alone. Cross-repo interfaces SHALL connect the repo to the
other participating repo through the interface resource; single-repository
interfaces SHALL connect the resource only to that repo. The table SHALL list
kind, name, type or ecosystem, direction relative to the repo, the other repo
when one exists, and that repo's role. Dependencies SHALL retain their existing
external-relationship-only rendering.

#### Scenario: Repo with a single-repository interface gets a section

- **WHEN** the compiled index contains an interface whose owner, producers, and
  consumers all name one repository
- **THEN** the organization document contains that repository's section with
  the interface resource in its diagram and table, without treating it as a
  conflict

#### Scenario: Cross-repo interface appears in every participating section

- **WHEN** an interface has participating repositories A and B
- **THEN** the organization document contains the interface resource in both
  A's and B's sections with the relevant direction and other-repository role

#### Scenario: Repo with external dependencies gets a section

- **WHEN** the compiled dependency index contains one or more dependency entries
  where a repo participates
  alongside at least one other repo (as producer or consumer)
- **THEN** the org diagram document contains that repo's section (or that repo's
  existing interface section
  is extended) with dependency edges rendered visually distinct from interface
  edges, and the repo's table
  includes rows for each external dependency

#### Scenario: Repo with both interfaces and dependencies gets one combined section

- **WHEN** a repo has at least one external interface and at least one external
  dependency
- **THEN** the repo's section contains a single relationship diagram showing
  both kinds of edges and a single
  table listing both, rather than two separate sections

### Requirement: Internal-only interfaces excluded from the org diagram

An interface entry SHALL be included in the organization document for every
repository named by its owner, producers, or consumers, even when that set has
one repository. A dependency entry SHALL remain internal-only, and excluded from
the organization document, when the union of its owner's repo, every producer
repo, and every consumer repo contains exactly one distinct repo name. A
cross-repo dependency SHALL be included for each participating repository.

#### Scenario: Single-repo interface is included

- **WHEN** an interface entry's owner, producers, and consumers all name the
  same single repo
- **THEN** that interface appears in that repo's organization-document section

#### Scenario: Cross-repo interface included in both repos' sections

- **WHEN** an interface entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section (direction: produces, other
  repo: B) and in repo B's section
  (direction: consumes, other repo: A)

### Requirement: Organization interface-conflict visibility

The generated organization architecture document SHALL render compiled interface
conflicts, including `potential-name-collision` findings, immediately below its
title under the exact heading `## Detected interface conflicts`. Each item SHALL
identify the interface name, its type or involved types, reason, details, and
affected repositories. The heading and section SHALL be omitted when there are
no compiled interface conflicts. Child-repository architecture documents SHALL
NOT be changed by this rendering.

#### Scenario: Organization document has conflicts

- **GIVEN** the compiled interface index contains a confirmed or potential
  interface conflict
- **WHEN** the organization architecture document is rendered
- **THEN** it contains `## Detected interface conflicts` below the title and an
  item describing that conflict

#### Scenario: Organization document has no conflicts

- **GIVEN** the compiled interface index has no interface conflicts
- **WHEN** the organization architecture document is rendered
- **THEN** it omits `## Detected interface conflicts`

### Requirement: Conflicting resources are highlighted in organization diagrams

The organization architecture renderer SHALL distinguish every interface
resource implicated by a compiled interface conflict. In Mermaid, it SHALL
render each affected resource through a dedicated resource node styled with a
red stroke and text and bold label. In the relationship table, it SHALL render
the affected resource name in bold with a red-circle indicator. Clean resources
SHALL retain the existing edge-label and table rendering.

#### Scenario: Confirmed interface conflict highlights its resource

- **GIVEN** a compiled conflict identifies one interface name and type
- **WHEN** an affected repository section is rendered
- **THEN** its Mermaid graph and relationship table visibly highlight that
  interface resource while unrelated resources remain unhighlighted

#### Scenario: Potential collision highlights every involved type

- **GIVEN** a `potential-name-collision` identifies one name with multiple
  involved types
- **WHEN** the organization architecture document is rendered
- **THEN** every relationship row and Mermaid resource for that name and each
  involved type is highlighted in every affected repository section

#### Scenario: Single-repo dependency excluded

- **WHEN** a dependency entry's owner, producer, and consumer all name the same
  single repo (a repo
  depending on its own published package)
- **THEN** that entry does not appear in any org diagram section

#### Scenario: Cross-repo dependency included in both repos' sections

- **WHEN** a dependency entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section (direction: produces, other
  repo: B) and in repo B's section
  (direction: consumes, other repo: A)

### Requirement: Linked dependency and interface edges deduplicate

The org diagram SHALL render a single edge between two repos, rather than two
separate edges, when a
dependency entry's `links_to_interface` names an interface entry that also
relates the same two repos (same
owner/producer and consumer pairing); the single edge SHALL be labeled to
indicate it represents both the
interface and the dependency.

#### Scenario: Linked generated client collapses to one edge

- **WHEN** a dependency entry has `links_to_interface` naming an interface entry
  that relates the same
  producer and consumer repos
- **THEN** the org diagram's relationship diagram for those repos shows one edge
  between them, not two, and
  the edge's label indicates both the interface and dependency names

#### Scenario: Unlinked dependency and interface between the same repos render separately

- **WHEN** a dependency entry and an interface entry both relate the same two
  repos but no
  `panopticon-dependency-of` hint links them
- **THEN** the org diagram renders both edges separately, without assuming they
  represent the same
  relationship

### Requirement: Diagram navigation uses plain links, not in-diagram click-through

Cross-repo navigation between the org diagram and per-repo diagrams SHALL use
ordinary markdown links (in the
org diagram's per-repo tables, and in each child repo's diagram section
back-link) rather than diagram-native
node click directives, because GitHub's rendering of Mermaid `click`-to-URL
navigation is not reliably
supported.

Links within a child repository's documentation tree SHALL use paths relative to
the document containing the link. The same child documentation is mirrored to
`docs/{repo}/` in the instance repo, so these local relative paths SHALL resolve
both in the child repository and at the mirrored instance location.

Because the org diagram document itself lives one level inside `docs/` (at
`docs/architecture.md`, not at
the instance repo root), every link it emits toward a child repo's own diagram
SHALL use `{repo}/architecture.md`
as the literal href — relative to the org diagram's own directory (`docs/`) —
never `docs/{repo}/architecture.md`.
The latter is a description of the resolved target's path from the instance repo
root, not a literal href:
using it as the href double-counts the `docs/` segment the org diagram file is
already inside, and GitHub
resolves it to the non-existent `docs/docs/{repo}/architecture.md`.

Each child architecture document's link to the org diagram SHALL instead be a
fully-qualified GitHub URL to
`{instance-repo-url}/blob/{instance_default_branch}/docs/architecture.md#{repo}`.
Doc generation SHALL obtain that URL from `python3 -m
panopticon.org_diagram_link` and use its output verbatim. It SHALL NOT author a
relative link to the org diagram, because no single relative href can resolve
from both the child repository and its mirrored instance location.

#### Scenario: User navigates from the org diagram to a child repo's diagram

- **WHEN** a user viewing the org diagram (`docs/architecture.md`) wants to see
  a specific repo's own
  component diagram
- **THEN** a markdown link in that repo's table row or section uses the literal
  href `{repo}/architecture.md`
  (no `docs/` prefix), which resolves relative to the org diagram's own
  directory to `docs/{repo}/architecture.md`
  in the instance repo

#### Scenario: A child-local documentation link works in both locations

- **GIVEN** a child architecture document contains a link to one of its local
  component documents
- **WHEN** the document is viewed in either the child repository or the
  instance repository's `docs/{repo}/` mirror
- **THEN** the link uses a path relative to the child architecture document and
  resolves to the corresponding child document in that location

#### Scenario: User navigates from a child repo's diagram to the org diagram

- **GIVEN** a child repo's `panopticon/config.json` has `repo: "svc-a"`,
  `instance: "acme/panopticon-instance"`, and
  `instance_default_branch: "main"`
- **WHEN** doc generation produces that repo's `## Architecture diagram` section
- **THEN** the section contains the markdown link `[org
  diagram](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`,
  using exactly the output of `python3 -m panopticon.org_diagram_link`

#### Scenario: Child-to-org back-link works before and after mirroring

- **GIVEN** doc generation has written a child architecture document's
  absolute org-diagram link
- **WHEN** the document is viewed in either the child repository or the
  instance repository's `docs/{repo}/` mirror
- **THEN** the link targets the same anchored org architecture document on
  GitHub

### Requirement: Org-diagram link script

A child repo SHALL provide a local script (`python3 -m
panopticon.org_diagram_link` or equivalent)
that prints exactly one line: a fully-qualified, directly resolvable GitHub URL
to this repo's
section of the org diagram —
`{instance-repo-url}/blob/{instance_default_branch}/docs/architecture.md#{repo}`
— built from `panopticon/config.json`'s `instance`, `instance_default_branch`,
and `repo` fields.

`panopticon/config.json` SHALL always be consulted first, and is sufficient on
its own whenever
`instance_default_branch` is already populated there (repo-initialization
capability, "Recorded
instance_default_branch is resolved deterministically, never guessed"; kept
current on every
bootstrap rerun by "Bootstrap script refreshes instance_default_branch on
rerun") — no network call
needed in that case. Only when the field is genuinely absent from config SHALL
the script fall back
to resolving the instance's default branch live via a `gh api` call, so a
developer isn't blocked by
a config gap that a one-off local lookup can paper over. If that live fallback
also fails (`gh`
missing, unauthenticated, or the API call errors), the script SHALL fail loudly
with a message
explaining both why (config gap and the live lookup's own failure) and how to
fix it — never guessing
a branch name.

This complements, rather than replaces, the relative link embedded in the repo's
own
`## Architecture diagram` section (see "Diagram navigation uses plain links, not
in-diagram
click-through"): that embedded link only resolves once this repo's docs have
been merged into the
instance repo. This script instead gives a developer sitting in the child repo's
own checkout, before
any merge, an immediately clickable link to the current org-wide picture — no
waiting for the next
merge, no need to already know the instance repo's URL or branch by heart.

#### Scenario: Script prints a resolvable deep link from config alone

- **GIVEN** a child repo's `panopticon/config.json` has `instance:
  "acme/panopticon-instance"`,
  `instance_default_branch: "main"`, and `repo: "svc-a"`
- **WHEN** the user runs the org-diagram link script
- **THEN** it prints exactly
  `https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a`
  by reading only local config — no GitHub API call, no instance-repo clone, no
  `PYTHONPATH`
  configuration

#### Scenario: Missing config field falls back to a live lookup

- **GIVEN** a child repo's `panopticon/config.json` has `instance:
  "acme/panopticon-instance"` and
  `repo: "svc-a"` but no `instance_default_branch` field, and `gh` is installed
  and authenticated
- **WHEN** the user runs the org-diagram link script
- **THEN** it resolves the instance's default branch live via `gh api` and
  prints the resulting link,
  without requiring the user to re-run bootstrap or finalization first

#### Scenario: Missing config field and failed live lookup fails loudly

- **GIVEN** a child repo's `panopticon/config.json` has no
  `instance_default_branch` field, and `gh`
  is either not installed or not authenticated
- **WHEN** the user runs the org-diagram link script
- **THEN** it exits non-zero with a message explaining that the field is missing
  and the live lookup
  also failed, and how to fix either — it SHALL NOT print a link built from a
  guessed branch name

### Requirement: Architecture diagrams link to analysis scope

A child architecture overview SHALL place
`[Panopticon analysis scope](operations.md#panopticon-analysis-scope)` directly below its required
diagram fence and retain the existing organization-diagram link. The linked operations document
SHALL visibly list the actual repository-relative illustrative directories excluded from analysis,
the default exact-component rule, and the explicit file/declaration hint syntax.

#### Scenario: Reader can inspect exclusions from the diagram

- **WHEN** a child documentation set contains an architecture diagram and operations document
- **THEN** the architecture document links directly to the operations analysis-scope section and
  that section lists the illustrative directories currently present in the repository

### Requirement: Child repo README links to both diagrams

A child repo's `README.md` SHALL contain, at the top of the file, two markdown
links in this order: the
repo's own architecture diagram link directly above the org architecture diagram
link. Both SHALL be labeled
with the repo name to distinguish them (`{repo} architecture` and `org
architecture`), never a bare
"architecture" label. These are written by the `panopticon-doc-generation` skill
as part of its normal
architecture-overview pass — the same agent-authored treatment as the existing
`## Architecture diagram`
back-link — not a separate deterministic script or a standalone CI check.

The own-repo link SHALL be a relative markdown link to this repo's
`architecture.md` at its configured `docs_location` (for example,
`docs/architecture.md`) and SHALL resolve in the child repository.

The org link SHALL be a fully-qualified GitHub URL, obtained by running `python3
-m
panopticon.org_diagram_link` and using its printed output verbatim — not by
re-deriving the URL or its
fallback behavior in the skill itself, since the script already implements the
correct config-first,
live-lookup-fallback, fail-loudly-never-guess logic (architecture-diagrams
capability, "Org-diagram link
script") and restating it elsewhere risks the two drifting apart.

#### Scenario: Doc generation writes both links in the correct order

- **GIVEN** a child repo with `panopticon/config.json` `repo: "svc-a"`,
  `instance:
  "acme/panopticon-instance"`, and `instance_default_branch: "main"`
- **WHEN** `panopticon-doc-generation` produces or refreshes `README.md`
- **THEN** the top of the file contains `[svc-a
  architecture](docs/architecture.md)` immediately followed by
  `[org
  architecture](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`,
  in
  that order — the second line matching exactly what `python3 -m
  panopticon.org_diagram_link` prints for
  this config

#### Scenario: Org diagram link script's own fallback and failure behavior applies unchanged

- **GIVEN** a child repo's `panopticon/config.json` has no
  `instance_default_branch`
- **WHEN** `panopticon-doc-generation` runs `python3 -m
  panopticon.org_diagram_link` to obtain the README or architecture-diagram org
  link
- **THEN** the script's own existing fallback (live lookup) and failure (loud
  error, never a guessed branch)
  behavior determines the outcome; if the script exits non-zero, doc generation
  stops and reports the gap
  rather than writing a partial or guessed link

### Requirement: Instance repo README links to the org diagram only

An instance repo's `README.md` SHALL contain, at the top of the file, exactly
one relative markdown link:
`[org architecture](docs/architecture.md)`. It SHALL NOT contain links to
individual child repos' diagrams —
the org diagram itself already enumerates every repo with an external interface
or dependency.

#### Scenario: Instance README contains only the org link

- **WHEN** an instance repo's `README.md` top matter is inspected
- **THEN** it contains `[org architecture](docs/architecture.md)` and no
  per-child-repo diagram links

### Requirement: Org diagram renders an explicit empty-state placeholder

`write_org_diagram` SHALL write a placeholder `docs/architecture.md` rather than
an empty or minimal document
when the compiled index (interfaces and dependencies combined) contains zero
repo sections: a diagram depicting
six nodes labeled `?`, connected to form a hexagon with no meaningful edge
labels, preceded by a markdown link
to `setup-guide.md#4-initialize-a-child-repo`. This placeholder SHALL be
produced by the same
deterministic render path every time `write_org_diagram` runs against a
zero-repo compiled index — not written
once and left stale — so it stays current if the org config or diagram format
changes before the first child
repo merges.

#### Scenario: write_org_diagram renders the placeholder for an empty compiled index

- **GIVEN** a compiled interface index and compiled dependency index that
  together contain zero repo sections
- **WHEN** `write_org_diagram` runs
- **THEN** it writes `docs/architecture.md` containing the link to
  `setup-guide.md#4-initialize-a-child-repo`
  followed by a diagram of six `?`-labeled nodes forming a hexagon

#### Scenario: First real merge replaces the placeholder

- **GIVEN** an instance repo whose `docs/architecture.md` is currently the
  empty-state placeholder
- **WHEN** the first child repo merges an interface or dependency that produces
  at least one repo section
- **THEN** `write_org_diagram` overwrites the placeholder with the real org
  diagram content

### Requirement: Template repo ships a non-dead placeholder and instance-appropriate README seed

The template repo SHALL ship the empty-state placeholder `docs/architecture.md`
(see "Org diagram renders an
explicit empty-state placeholder") directly in its tracked tree, so a newly
created instance repo's
`README.md` org-architecture link is never dead, even before any
`write_org_diagram` run.

The template repo's own `README.md` Overview section (the paragraph between the
`## Overview` heading and the
logo image) SHALL be org-agnostic instance-appropriate boilerplate plus the
`[org architecture]
(docs/architecture.md)` link, followed by a maintainer note — placed between
that text and the logo image —
instructing the org to replace the paragraph with a description specific to
their organization. No dynamic
substitution of org-specific content SHALL be assumed or attempted, since no
reliable event fires when a
repository is created from a template.

#### Scenario: Fresh instance repo has a working architecture link on day one

- **GIVEN** an organization creates a new instance repo via "Use this template"
- **WHEN** they open the newly created repo's `README.md` before running any
  Panopticon tooling
- **THEN** the `[org architecture](docs/architecture.md)` link resolves to the
  shipped placeholder content,
  not a broken link

#### Scenario: Maintainer note appears between the overview text and the logo

- **WHEN** the template repo's `README.md` is inspected
- **THEN** the Overview section reads: instance-appropriate boilerplate text,
  then the org architecture link,
  then a maintainer note instructing the org to personalize the paragraph, then
  the logo image — in that
  order

### Requirement: Org diagram is template-declared and instance-owned during sync

The template SHALL declare `docs/architecture.md` as an instance-owned generated
path for template-sync
merges. The template's tracked copy is an installable empty-state placeholder,
not the durable source of
truth after an instance has generated or otherwise acquired its own copy. When
the path exists on both
sides of a template merge, the instance's current copy SHALL win. When it exists
only in the incoming
template, the placeholder SHALL be installed.

This classification SHALL be fixed by the template and SHALL NOT be modeled as
protected JSON configuration,
an entry in `PROTECTED_CONFIG_FILES`, an org-declared `protected_paths`
customization, or a tracked
`.gitattributes` rule. It SHALL use the template-sync workflow's per-checkout
`.git/info/attributes`
registration and existing `merge.ours.driver true` configuration.

#### Scenario: Generated instance diagram is preserved

- **GIVEN** both the instance and incoming template contain
  `docs/architecture.md`
- **WHEN** template sync merges the histories and Git requires a path-level
  merge decision
- **THEN** the instance's current generated content is retained

#### Scenario: Placeholder bootstraps a missing diagram

- **GIVEN** the incoming template contains the empty-state placeholder and the
  instance has no
  `docs/architecture.md`
- **WHEN** template sync merges the histories
- **THEN** the placeholder is added to the instance and its README architecture
  link resolves

#### Scenario: Generated path is not reported as customization

- **WHEN** template sync registers `docs/architecture.md` in
  `.git/info/attributes`
- **THEN** the workflow identifies it as a template-declared generated path and
  does not describe it as
protected configuration or org customization

### Requirement: Complete generated child architecture link protocol

The system SHALL apply the same link protocol to every generated child
architecture navigation surface through the `panopticon-doc-generation` skill
and its architecture overview template. The generated link surfaces include
the child README and child architecture overview. Links from either surface to
the organization diagram SHALL use exactly the absolute URL printed by
`python3 -m panopticon.org_diagram_link`. Links between documents in the child
documentation tree SHALL remain relative to the document that contains them.
The instance org diagram's links to mirrored child architecture documents SHALL
remain `{repo}/architecture.md`, relative to `docs/architecture.md`.

When the skill refreshes a child architecture overview, it SHALL replace a
legacy relative org-diagram back-link with the resolver-produced absolute URL.

#### Scenario: Child architecture overview uses the org-link resolver

- **GIVEN** a child repo with `repo: "svc-a"`,
  `instance: "acme/panopticon-instance"`, and
  `instance_default_branch: "main"`
- **WHEN** doc generation creates or refreshes its architecture overview
- **THEN** the `## Architecture diagram` section contains
  `[org diagram](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`
  from `python3 -m panopticon.org_diagram_link`, not a relative org-diagram
  link

#### Scenario: All generated architecture navigation surfaces use their protocol

- **WHEN** the child README, child architecture overview, and instance org
  diagram are generated or refreshed
- **THEN** child-to-org links are resolver-produced absolute URLs, child-local
  links are document-relative, and org-to-child links use
  `{repo}/architecture.md`
