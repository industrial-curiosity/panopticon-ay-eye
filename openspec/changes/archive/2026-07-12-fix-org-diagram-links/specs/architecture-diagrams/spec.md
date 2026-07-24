# Architecture Diagrams Spec

## MODIFIED Requirements

### Requirement: Diagram navigation uses plain links, not in-diagram click-through

Cross-repo navigation between the org diagram and per-repo diagrams SHALL use
ordinary markdown links (in the
org diagram's per-repo tables, and in each child repo's diagram section
back-link) rather than diagram-native
node click directives, because GitHub's rendering of Mermaid `click`-to-URL
navigation is not reliably
supported.

All of this navigation SHALL use relative markdown links, never absolute GitHub
URLs. Every child repo's
documentation is merged into the instance repo at `docs/{repo}/` on every push
to its default branch
(master-sync capability), and the org diagram lives at the instance repo's own
`docs/architecture.md`.
Once merged, the org diagram and every repo's own diagram section are files in
the *same* repository
tree — the instance repo's — so an ordinary relative link between them resolves
correctly both on GitHub's
web UI and when the instance repo is checked out locally, with no dependency on
repo URLs, branch names,
or any config field. This holds regardless of where a repo's `docs_location`
places the file *before*
merge: the merge step always normalizes every repo's docs into the same
`docs/{repo}/` layout (one level
under the instance repo's `docs/`), so the relative path from any repo's merged
`architecture.md` up to
the org diagram is always `../architecture.md`, identically for every repo.

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

A child repo's own local `## Architecture diagram` section back-link is
therefore authored for its
*post-merge* location in the instance repo, not its current location in the
child repo's own checkout.
The link SHALL NOT be expected to resolve when viewed directly in the child repo
before that repo's docs
have been merged into the instance — it SHALL resolve once merged, which is the
intended point of review:
architecture diagrams are reviewed in the instance repo, where the full
cross-repo picture exists, not by
browsing individual child repos in isolation.

#### Scenario: User navigates from the org diagram to a child repo's diagram

- **WHEN** a user viewing the org diagram (`docs/architecture.md`) wants to see
  a specific repo's own
  component diagram
- **THEN** a markdown link in that repo's table row or section uses the literal
  href `{repo}/architecture.md`
  (no `docs/` prefix), which resolves relative to the org diagram's own
  directory to `docs/{repo}/architecture.md`
  in the instance repo

#### Scenario: User navigates from a child repo's diagram to the org diagram

- **GIVEN** a child repo's `panopticon/config.json` has `repo: "svc-a"`
- **WHEN** doc generation produces that repo's `## Architecture diagram` section
- **THEN** the section contains the markdown link `[org
  diagram](../architecture.md#svc-a)` — a relative
  link, not an absolute URL, that resolves correctly once this file is merged to
  `docs/svc-a/architecture.md` in the instance repo

#### Scenario: Back-link shape is identical across repos regardless of docs_location

- **GIVEN** two child repos with different `docs_location` values (`docs/` and
  `documentation/`)
- **WHEN** each produces its `## Architecture diagram` section's org-diagram
  back-link
- **THEN** both use the identical relative path `../architecture.md` (only the
  `#{repo}` anchor differs) —
  because the merge target (`docs/{repo}/`) is the same for every repo
  regardless of the source repo's own
  `docs_location`
