# Architecture diagrams specification delta

## MODIFIED Requirements

### Requirement: Per-repo diagram section

Each repo's `architecture.md` SHALL contain a `## Architecture diagram` section directly under
which is exactly one fenced code block tagged with the configured format's language identifier,
depicting the repo's components and their relationships. This section is part of the
architecture-overview documentation layer (doc-generation capability) and SHALL be agent-drawn
and grounded in the actual code, following the same rules as the rest of that layer. Directly below
the diagram, it SHALL include proper markdown links to the repository's organization-diagram anchor
and to `operations.md#panopticon-analysis-scope`.

#### Scenario: Diagram section present after doc generation

- **WHEN** doc generation produces or updates `architecture.md`
- **THEN** the file contains a `## Architecture diagram` section with one fenced code block in the configured format depicting this repo's components and their relationships

#### Scenario: Diagram links back to the org diagram

- **WHEN** doc generation produces the `## Architecture diagram` section
- **THEN** the section includes a proper markdown link, not a bare URL, to the org diagram's anchor for this repo, built exactly as specified in `Diagram navigation uses plain links, not in-diagram click-through`

#### Scenario: Diagram links to analysis scope

- **WHEN** doc generation produces the `## Architecture diagram` section
- **THEN** directly below the diagram it includes a proper relative markdown link to `operations.md#panopticon-analysis-scope`
