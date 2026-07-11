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
- **THEN** the section includes a markdown link to the org diagram's anchor for this repo in the instance
  repo, derived from `panopticon/config.json`'s `instance` field

### Requirement: Org diagram document shape

The org diagram (rendered deterministically from the compiled index by the master-sync capability) SHALL be a
single document at the instance repo root containing one section per repo that has at least one external
interface, ordered alphabetically by repo name. Each section SHALL contain a relationship diagram (this repo
as the center node, one node per other repo it relates to, edges labeled by interface name) followed by a
table listing each external interface: name, type, direction relative to this repo, the other repo, and that
repo's role (owner, producer, or consumer).

#### Scenario: Repo with external interfaces gets a section

- **WHEN** the compiled index contains one or more interfaces where a repo participates alongside at least
  one other repo
- **THEN** the org diagram document contains that repo's section, alphabetically placed, with its
  relationship diagram and interface table

#### Scenario: Repo with only internal interfaces is omitted

- **WHEN** every one of a repo's interface entries is internal-only (see the internal-only exclusion rule)
- **THEN** the org diagram document contains no section for that repo

### Requirement: Internal-only interfaces excluded from the org diagram

An interface entry SHALL be considered internal-only, and excluded from the org diagram entirely, when the
union of its owner's repo, every producer repo, and every consumer repo contains exactly one distinct repo
name. An entry SHALL be considered external for a given repo, and included in that repo's section, only when
this union contains more than one distinct repo name and includes that repo.

#### Scenario: Single-repo interface excluded

- **WHEN** an interface entry's owner, producers, and consumers all name the same single repo
- **THEN** that entry does not appear in any org diagram section

#### Scenario: Cross-repo interface included in both repos' sections

- **WHEN** an interface entry's producer is repo A and consumer is repo B
- **THEN** the entry appears in repo A's section (direction: produces, other repo: B) and in repo B's section
  (direction: consumes, other repo: A)

### Requirement: Diagram navigation uses plain links, not in-diagram click-through

Cross-repo navigation between the org diagram and per-repo diagrams SHALL use ordinary markdown links (in the
org diagram's per-repo tables, and in each child repo's diagram section back-link) rather than diagram-native
node click directives, because GitHub's rendering of Mermaid `click`-to-URL navigation is not reliably
supported.

#### Scenario: User navigates from the org diagram to a child repo's diagram

- **WHEN** a user viewing the org diagram wants to see a specific repo's own component diagram
- **THEN** a markdown link in that repo's table row or section leads to `docs/{repo}/architecture.md` in the
  instance repo

#### Scenario: User navigates from a child repo's diagram to the org diagram

- **WHEN** a user viewing a child repo's `## Architecture diagram` section wants to see the org-wide picture
- **THEN** a markdown link in that section leads to the org diagram document at this repo's anchor
