## MODIFIED Requirements

### Requirement: Diagram navigation uses plain links, not in-diagram click-through

Cross-repo navigation between the org diagram and per-repo diagrams SHALL use
ordinary markdown links (in the org diagram's per-repo tables, and in each
child repo's diagram section back-link) rather than diagram-native node click
directives, because GitHub's rendering of Mermaid `click`-to-URL navigation is
not reliably supported.

Links within a child repository's documentation tree SHALL use paths relative to
the document containing the link. The same child documentation is mirrored to
`docs/{repo}/` in the instance repo, so these local relative paths SHALL resolve
both in the child repository and at the mirrored instance location.

The org diagram document itself lives at `docs/architecture.md` in the instance
repo. Every link it emits toward a child repo's mirrored architecture document
SHALL use `{repo}/architecture.md` as the literal href — relative to the org
diagram's own directory (`docs/`) — never `docs/{repo}/architecture.md`.
Using the latter double-counts the `docs/` segment and resolves to the
non-existent `docs/docs/{repo}/architecture.md`.

Each child architecture document's link to the org diagram SHALL instead be a
fully-qualified GitHub URL to
`{instance-repo-url}/blob/{instance_default_branch}/docs/architecture.md#{repo}`.
Doc generation SHALL obtain that URL from `python3 -m
panopticon.org_diagram_link` and use its output verbatim. It SHALL NOT author a
relative link to the org diagram, because no single relative href can resolve
from both the child repository and its mirrored instance location.

#### Scenario: User navigates from the org diagram to a child repo's diagram

- **WHEN** a user viewing the org diagram (`docs/architecture.md`) wants to see
  a specific repo's own component diagram
- **THEN** a markdown link in that repo's table row or section uses the literal
  href `{repo}/architecture.md` (no `docs/` prefix), which resolves relative to
  the org diagram's own directory to `docs/{repo}/architecture.md` in the
  instance repo

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

### Requirement: Child repo README links to both diagrams

A child repo's `README.md` SHALL contain, at the top of the file, two markdown
links in this order: the repo's own architecture diagram link directly above
the org architecture diagram link. Both SHALL be labeled with the repo name to
distinguish them (`{repo} architecture` and `org architecture`), never a bare
"architecture" label. These are written by the `panopticon-doc-generation`
skill as part of its normal architecture-overview pass, not by a separate
deterministic script or standalone CI check.

The own-repo link SHALL be a relative markdown link to this repo's
`architecture.md` at its configured `docs_location` (for example,
`docs/architecture.md`) and SHALL resolve in the child repository. The org link
SHALL be a fully-qualified GitHub URL obtained by running `python3 -m
panopticon.org_diagram_link` and using its printed output verbatim. The skill
SHALL NOT re-derive the URL or its fallback behavior.

#### Scenario: Doc generation writes both links in the correct order

- **GIVEN** a child repo with `panopticon/config.json` `repo: "svc-a"`,
  `instance: "acme/panopticon-instance"`, and
  `instance_default_branch: "main"`
- **WHEN** `panopticon-doc-generation` produces or refreshes `README.md`
- **THEN** the top of the file contains `[svc-a
  architecture](docs/architecture.md)` immediately followed by `[org
  architecture](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`,
  in that order — the second line matching exactly what `python3 -m
  panopticon.org_diagram_link` prints for this config

#### Scenario: Org diagram link script's own fallback and failure behavior applies unchanged

- **GIVEN** a child repo's `panopticon/config.json` has no
  `instance_default_branch`
- **WHEN** `panopticon-doc-generation` runs `python3 -m
  panopticon.org_diagram_link` to obtain the README or architecture-diagram org
  link
- **THEN** the script's own existing fallback and failure behavior determines
  the outcome; if the script exits non-zero, doc generation stops and reports
  the gap rather than writing a partial or guessed link
