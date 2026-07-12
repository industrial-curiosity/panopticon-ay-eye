## MODIFIED Requirements

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

A child repo's own local `## Architecture diagram` section back-link is therefore authored for its
*post-merge* location in the instance repo, not its current location in the child repo's own checkout.
The link SHALL NOT be expected to resolve when viewed directly in the child repo before that repo's docs
have been merged into the instance — it SHALL resolve once merged, which is the intended point of review:
architecture diagrams are reviewed in the instance repo, where the full cross-repo picture exists, not by
browsing individual child repos in isolation.

#### Scenario: User navigates from the org diagram to a child repo's diagram

- **WHEN** a user viewing the org diagram wants to see a specific repo's own component diagram
- **THEN** a markdown link in that repo's table row or section leads to `docs/{repo}/architecture.md` in the
  instance repo

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
