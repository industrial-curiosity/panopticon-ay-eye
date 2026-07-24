# Architecture Diagrams Spec

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Per-repo diagram section

Each repo's `architecture.md` SHALL contain a `## Architecture diagram` section
directly under which is
exactly one fenced code block tagged with the configured format's language
identifier, depicting the repo's
components and their relationships. This section is part of the
architecture-overview documentation layer
(doc-generation capability) and SHALL be agent-drawn and grounded in the actual
code, following the same
rules as the rest of that layer.

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

- **WHEN** a user viewing the org diagram wants to see a specific repo's own
  component diagram
- **THEN** a markdown link in that repo's table row or section leads to
  `docs/{repo}/architecture.md` in the
  instance repo

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
