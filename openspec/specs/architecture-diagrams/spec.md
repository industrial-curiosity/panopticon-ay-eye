# Architecture Diagrams Specification

## Purpose

Define how Panopticon generates, links, configures, and synchronizes repository and organization diagrams.
## Requirements
### Requirement: Diagram format configuration

Diagram rendering format SHALL be configurable per instance repo via `panopticon.diagram.config.json` at the
instance repo root, with `format` defaulting to `mermaid` when the file is absent. This configuration SHALL
NOT be overwritten by the `sync-from-template` workflow's merge (see the repo-initialization capability's
protected-config mechanism). Child repos and CI checks SHALL read the effective format from the instance
repo's checked-out configuration rather than assuming a hardcoded value.

#### Scenario: Default format with no config file

- **WHEN** an instance repo has no `panopticon.diagram.config.json`
- **THEN** the effective diagram format is `mermaid`

#### Scenario: Instance overrides the format

- **WHEN** an instance repo's `panopticon.diagram.config.json` sets an explicit `format` value
- **THEN** doc generation, the diagram-existence check, and org diagram rendering all use that configured
  format consistently

#### Scenario: Unsupported format fails loudly

- **WHEN** `panopticon.diagram.config.json` names a format with no implemented renderer
- **THEN** the diagram-existence check and the org-diagram rebuild both fail with an explicit "unknown
  diagram format" error rather than silently skipping diagram generation

### Requirement: Per-repo diagram section

Each repo's `architecture.md` SHALL contain a `## Architecture diagram` section directly under which is
exactly one fenced code block tagged with the configured format's language identifier, depicting the repo's
components and their relationships. This section is part of the architecture-overview documentation layer
(doc-generation capability) and SHALL be agent-drawn and grounded in the actual code, following the same
rules as the rest of that layer.

#### Scenario: Diagram section present after doc generation

- **WHEN** doc generation produces or updates `architecture.md`
- **THEN** the file contains a `## Architecture diagram` section with one fenced code block in the configured
  format depicting this repo's components and their relationships

#### Scenario: Diagram links back to the org diagram

- **WHEN** doc generation produces the `## Architecture diagram` section
- **THEN** the section includes a proper markdown link (not a bare URL) to the org diagram's anchor for
  this repo, built exactly as specified in "Diagram navigation uses plain links, not in-diagram
  click-through"

### Requirement: Org diagram document shape

The org diagram (rendered deterministically from the compiled index by the master-sync capability) SHALL be a
single document at the instance repo root containing one section per repo that has at least one external
interface or dependency, ordered alphabetically by repo name. Each section SHALL contain a relationship
diagram (this repo as the center node, one node per other repo it relates to, edges labeled by interface or
dependency name and visually distinguished by kind — dashed edges for interfaces, solid edges for
dependencies) followed by a table listing each external interface or dependency: kind (interface or
dependency), name, type or ecosystem, direction relative to this repo, the other repo, and that repo's role
(owner, producer, or consumer).

#### Scenario: Repo with external interfaces gets a section

- **WHEN** the compiled index contains one or more interfaces where a repo participates alongside at least
  one other repo
- **THEN** the org diagram document contains that repo's section, alphabetically placed, with its
  relationship diagram and interface table

#### Scenario: Repo with only internal interfaces is omitted

- **WHEN** every one of a repo's interface entries is internal-only (see the internal-only exclusion rule)
- **THEN** the org diagram document contains no section for that repo

#### Scenario: Repo with external dependencies gets a section

- **WHEN** the compiled dependency index contains one or more dependency entries where a repo participates
  alongside at least one other repo (as producer or consumer)
- **THEN** the org diagram document contains that repo's section (or that repo's existing interface section
  is extended) with dependency edges rendered visually distinct from interface edges, and the repo's table
  includes rows for each external dependency

#### Scenario: Repo with both interfaces and dependencies gets one combined section

- **WHEN** a repo has at least one external interface and at least one external dependency
- **THEN** the repo's section contains a single relationship diagram showing both kinds of edges and a single
  table listing both, rather than two separate sections

### Requirement: Internal-only interfaces excluded from the org diagram

An interface or dependency entry SHALL be considered internal-only, and excluded from the org diagram
entirely, when the union of its owner's repo, every producer repo, and every consumer repo contains exactly
one distinct repo name. An entry SHALL be considered external for a given repo, and included in that repo's
section, only when this union contains more than one distinct repo name and includes that repo. This applies
identically to interface entries and dependency entries.

#### Scenario: Single-repo interface excluded

- **WHEN** an interface entry's owner, producers, and consumers all name the same single repo
- **THEN** that entry does not appear in any org diagram section

#### Scenario: Cross-repo interface included in both repos' sections

- **WHEN** an interface entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section (direction: produces, other repo: B) and in repo B's section
  (direction: consumes, other repo: A)

#### Scenario: Single-repo dependency excluded

- **WHEN** a dependency entry's owner, producer, and consumer all name the same single repo (a repo
  depending on its own published package)
- **THEN** that entry does not appear in any org diagram section

#### Scenario: Cross-repo dependency included in both repos' sections

- **WHEN** a dependency entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section (direction: produces, other repo: B) and in repo B's section
  (direction: consumes, other repo: A)

### Requirement: Linked dependency and interface edges deduplicate

The org diagram SHALL render a single edge between two repos, rather than two separate edges, when a
dependency entry's `links_to_interface` names an interface entry that also relates the same two repos (same
owner/producer and consumer pairing); the single edge SHALL be labeled to indicate it represents both the
interface and the dependency.

#### Scenario: Linked generated client collapses to one edge

- **WHEN** a dependency entry has `links_to_interface` naming an interface entry that relates the same
  producer and consumer repos
- **THEN** the org diagram's relationship diagram for those repos shows one edge between them, not two, and
  the edge's label indicates both the interface and dependency names

#### Scenario: Unlinked dependency and interface between the same repos render separately

- **WHEN** a dependency entry and an interface entry both relate the same two repos but no
  `panopticon-dependency-of` hint links them
- **THEN** the org diagram renders both edges separately, without assuming they represent the same
  relationship

### Requirement: Diagram navigation uses plain links, not in-diagram click-through

Cross-repo navigation between the org diagram and per-repo diagrams SHALL use ordinary markdown links (in the
org diagram's per-repo tables, and in each child repo's diagram section back-link) rather than diagram-native
node click directives, because GitHub's rendering of Mermaid `click`-to-URL navigation is not reliably
supported.

All of this navigation SHALL use relative markdown links, never absolute GitHub URLs. Every child repo's
documentation is merged into the instance repo at `docs/{repo}/` on every push to its default branch
(master-sync capability), and the org diagram lives at the instance repo's own `docs/architecture.md`.
Once merged, the org diagram and every repo's own diagram section are files in the *same* repository
tree — the instance repo's — so an ordinary relative link between them resolves correctly both on GitHub's
web UI and when the instance repo is checked out locally, with no dependency on repo URLs, branch names,
or any config field. This holds regardless of where a repo's `docs_location` places the file *before*
merge: the merge step always normalizes every repo's docs into the same `docs/{repo}/` layout (one level
under the instance repo's `docs/`), so the relative path from any repo's merged `architecture.md` up to
the org diagram is always `../architecture.md`, identically for every repo.

Because the org diagram document itself lives one level inside `docs/` (at `docs/architecture.md`, not at
the instance repo root), every link it emits toward a child repo's own diagram SHALL use `{repo}/architecture.md`
as the literal href — relative to the org diagram's own directory (`docs/`) — never `docs/{repo}/architecture.md`.
The latter is a description of the resolved target's path from the instance repo root, not a literal href:
using it as the href double-counts the `docs/` segment the org diagram file is already inside, and GitHub
resolves it to the non-existent `docs/docs/{repo}/architecture.md`.

A child repo's own local `## Architecture diagram` section back-link is therefore authored for its
*post-merge* location in the instance repo, not its current location in the child repo's own checkout.
The link SHALL NOT be expected to resolve when viewed directly in the child repo before that repo's docs
have been merged into the instance — it SHALL resolve once merged, which is the intended point of review:
architecture diagrams are reviewed in the instance repo, where the full cross-repo picture exists, not by
browsing individual child repos in isolation.

#### Scenario: User navigates from the org diagram to a child repo's diagram

- **WHEN** a user viewing the org diagram (`docs/architecture.md`) wants to see a specific repo's own
  component diagram
- **THEN** a markdown link in that repo's table row or section uses the literal href `{repo}/architecture.md`
  (no `docs/` prefix), which resolves relative to the org diagram's own directory to `docs/{repo}/architecture.md`
  in the instance repo

#### Scenario: User navigates from a child repo's diagram to the org diagram

- **GIVEN** a child repo's `panopticon/config.json` has `repo: "svc-a"`
- **WHEN** doc generation produces that repo's `## Architecture diagram` section
- **THEN** the section contains the markdown link `[org diagram](../architecture.md#svc-a)` — a relative
  link, not an absolute URL, that resolves correctly once this file is merged to
  `docs/svc-a/architecture.md` in the instance repo

#### Scenario: Back-link shape is identical across repos regardless of docs_location

- **GIVEN** two child repos with different `docs_location` values (`docs/` and `documentation/`)
- **WHEN** each produces its `## Architecture diagram` section's org-diagram back-link
- **THEN** both use the identical relative path `../architecture.md` (only the `#{repo}` anchor differs) —
  because the merge target (`docs/{repo}/`) is the same for every repo regardless of the source repo's own
  `docs_location`

### Requirement: Org-diagram link script

A child repo SHALL provide a local script (`python3 -m panopticon.org_diagram_link` or equivalent)
that prints exactly one line: a fully-qualified, directly resolvable GitHub URL to this repo's
section of the org diagram — `{instance-repo-url}/blob/{instance_default_branch}/docs/architecture.md#{repo}`
— built from `panopticon/config.json`'s `instance`, `instance_default_branch`, and `repo` fields.

`panopticon/config.json` SHALL always be consulted first, and is sufficient on its own whenever
`instance_default_branch` is already populated there (repo-initialization capability, "Recorded
instance_default_branch is resolved deterministically, never guessed"; kept current on every
bootstrap rerun by "Bootstrap script refreshes instance_default_branch on rerun") — no network call
needed in that case. Only when the field is genuinely absent from config SHALL the script fall back
to resolving the instance's default branch live via a `gh api` call, so a developer isn't blocked by
a config gap that a one-off local lookup can paper over. If that live fallback also fails (`gh`
missing, unauthenticated, or the API call errors), the script SHALL fail loudly with a message
explaining both why (config gap and the live lookup's own failure) and how to fix it — never guessing
a branch name.

This complements, rather than replaces, the relative link embedded in the repo's own
`## Architecture diagram` section (see "Diagram navigation uses plain links, not in-diagram
click-through"): that embedded link only resolves once this repo's docs have been merged into the
instance repo. This script instead gives a developer sitting in the child repo's own checkout, before
any merge, an immediately clickable link to the current org-wide picture — no waiting for the next
merge, no need to already know the instance repo's URL or branch by heart.

#### Scenario: Script prints a resolvable deep link from config alone

- **GIVEN** a child repo's `panopticon/config.json` has `instance: "acme/panopticon-instance"`,
  `instance_default_branch: "main"`, and `repo: "svc-a"`
- **WHEN** the user runs the org-diagram link script
- **THEN** it prints exactly `https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a`
  by reading only local config — no GitHub API call, no instance-repo clone, no `PYTHONPATH`
  configuration

#### Scenario: Missing config field falls back to a live lookup

- **GIVEN** a child repo's `panopticon/config.json` has `instance: "acme/panopticon-instance"` and
  `repo: "svc-a"` but no `instance_default_branch` field, and `gh` is installed and authenticated
- **WHEN** the user runs the org-diagram link script
- **THEN** it resolves the instance's default branch live via `gh api` and prints the resulting link,
  without requiring the user to re-run bootstrap or finalization first

#### Scenario: Missing config field and failed live lookup fails loudly

- **GIVEN** a child repo's `panopticon/config.json` has no `instance_default_branch` field, and `gh`
  is either not installed or not authenticated
- **WHEN** the user runs the org-diagram link script
- **THEN** it exits non-zero with a message explaining that the field is missing and the live lookup
  also failed, and how to fix either — it SHALL NOT print a link built from a guessed branch name

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

The org link SHALL be a fully-qualified GitHub URL, obtained by running `python3 -m
panopticon.org_diagram_link` and using its printed output verbatim — not by re-deriving the URL or its
fallback behavior in the skill itself, since the script already implements the correct config-first,
live-lookup-fallback, fail-loudly-never-guess logic (architecture-diagrams capability, "Org-diagram link
script") and restating it elsewhere risks the two drifting apart.

#### Scenario: Doc generation writes both links in the correct order

- **GIVEN** a child repo with `panopticon/config.json` `repo: "svc-a"`, `instance:
  "acme/panopticon-instance"`, and `instance_default_branch: "main"`
- **WHEN** `panopticon-doc-generation` produces or refreshes `README.md`
- **THEN** the top of the file contains `[svc-a architecture](docs/architecture.md)` immediately followed by
  `[org architecture](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`, in
  that order — the second line matching exactly what `python3 -m panopticon.org_diagram_link` prints for
  this config

#### Scenario: Org diagram link script's own fallback and failure behavior applies unchanged

- **GIVEN** a child repo's `panopticon/config.json` has no `instance_default_branch`
- **WHEN** `panopticon-doc-generation` runs `python3 -m panopticon.org_diagram_link` to obtain the README org
  link
- **THEN** the script's own existing fallback (live lookup) and failure (loud error, never a guessed branch)
  behavior determines the outcome; if the script exits non-zero, doc generation stops and reports the gap
  rather than writing a partial or guessed link

### Requirement: Instance repo README links to the org diagram only

An instance repo's `README.md` SHALL contain, at the top of the file, exactly one relative markdown link:
`[org architecture](docs/architecture.md)`. It SHALL NOT contain links to individual child repos' diagrams —
the org diagram itself already enumerates every repo with an external interface or dependency.

#### Scenario: Instance README contains only the org link

- **WHEN** an instance repo's `README.md` top matter is inspected
- **THEN** it contains `[org architecture](docs/architecture.md)` and no per-child-repo diagram links

### Requirement: Org diagram renders an explicit empty-state placeholder

`write_org_diagram` SHALL write a placeholder `docs/architecture.md` rather than an empty or minimal document
when the compiled index (interfaces and dependencies combined) contains zero repo sections: a diagram depicting
six nodes labeled `?`, connected to form a hexagon with no meaningful edge labels, preceded by a markdown link
to `setup-guide.md#4-initialize-a-child-repo`. This placeholder SHALL be produced by the same
deterministic render path every time `write_org_diagram` runs against a zero-repo compiled index — not written
once and left stale — so it stays current if the org config or diagram format changes before the first child
repo merges.

#### Scenario: write_org_diagram renders the placeholder for an empty compiled index

- **GIVEN** a compiled interface index and compiled dependency index that together contain zero repo sections
- **WHEN** `write_org_diagram` runs
- **THEN** it writes `docs/architecture.md` containing the link to `setup-guide.md#4-initialize-a-child-repo`
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

### Requirement: Org diagram is template-declared and instance-owned during sync

The template SHALL declare `docs/architecture.md` as an instance-owned generated path for template-sync
merges. The template's tracked copy is an installable empty-state placeholder, not the durable source of
truth after an instance has generated or otherwise acquired its own copy. When the path exists on both
sides of a template merge, the instance's current copy SHALL win. When it exists only in the incoming
template, the placeholder SHALL be installed.

This classification SHALL be fixed by the template and SHALL NOT be modeled as protected JSON configuration,
an entry in `PROTECTED_CONFIG_FILES`, an org-declared `protected_paths` customization, or a tracked
`.gitattributes` rule. It SHALL use the template-sync workflow's per-checkout `.git/info/attributes`
registration and existing `merge.ours.driver true` configuration.

#### Scenario: Generated instance diagram is preserved

- **GIVEN** both the instance and incoming template contain `docs/architecture.md`
- **WHEN** template sync merges the histories and Git requires a path-level merge decision
- **THEN** the instance's current generated content is retained

#### Scenario: Placeholder bootstraps a missing diagram

- **GIVEN** the incoming template contains the empty-state placeholder and the instance has no
  `docs/architecture.md`
- **WHEN** template sync merges the histories
- **THEN** the placeholder is added to the instance and its README architecture link resolves

#### Scenario: Generated path is not reported as customization

- **WHEN** template sync registers `docs/architecture.md` in `.git/info/attributes`
- **THEN** the workflow identifies it as a template-declared generated path and does not describe it as
  protected configuration or org customization

