# {Repo name} — architecture overview

## Purpose

{One or two paragraphs: what this repo exists to do, for whom, and the problem it solves.}

## Components

{One bullet per component, linking to its per-component doc:}

- [{component-name}](components/{component-name}.md) — {one-line responsibility}

## Architecture diagram

{A single fenced code block, tagged with the instance's configured diagram format (default
`mermaid`), depicting this repo's components and how they relate — grounded in the actual code,
same discipline as the rest of this layer. Directly below the block, add a markdown link to this
repo's section in the org diagram. Run `python3 -m panopticon.org_diagram_link` and use its output
verbatim, for example `[org
diagram](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`. This
must be an absolute GitHub URL so it works in both the child repository and the mirrored instance
documentation. Replace any existing relative org-diagram back-link with this URL. All links to
documents within this child documentation tree remain relative to this document, for example
`components/{component-name}.md`.}

```mermaid
{diagram content}
```

[org diagram]({output of `python3 -m panopticon.org_diagram_link`})

## Data flow

{How data moves through the system: entry points, processing stages, storage, outputs. A short
ordered narrative or a text diagram. Name the interfaces involved using their canonical index
names.}

## Dependencies

{External systems this repo depends on (services, data stores, queues, third-party APIs) and what
breaks when each is unavailable. Interfaces consumed from other repos belong here; link to
[interfaces.md](interfaces.md) rather than duplicating details.}
