# {Repo name} — architecture overview

## Purpose

{One or two paragraphs: what this repo exists to do, for whom, and the problem it solves.}

## Components

{One bullet per component, linking to its per-component doc:}

- [{component-name}](components/{component-name}.md) — {one-line responsibility}

## Architecture diagram

{A single fenced code block, tagged with the instance's configured diagram format (default
`mermaid`), depicting this repo's components and how they relate — grounded in the actual code,
same discipline as the rest of this layer. Directly below the block, a markdown link back to this
repo's section in the org diagram: `[org diagram](../architecture.md#{repo})` (`{repo}` from
`panopticon/config.json`'s `repo` field) — a *relative* link, not an absolute URL: this repo's docs
are merged into the instance repo at `docs/{repo}/` on every push, landing this file at
`docs/{repo}/architecture.md` alongside the org diagram at `docs/architecture.md`, so `../architecture.md`
resolves correctly there. It will not resolve when viewed directly in this repo before that merge
happens — that's expected, not a bug: architecture diagrams are reviewed in the instance repo.}

```mermaid
{diagram content}
```

[org diagram](../architecture.md#{repo})

## Data flow

{How data moves through the system: entry points, processing stages, storage, outputs. A short
ordered narrative or a text diagram. Name the interfaces involved using their canonical index
names.}

## Dependencies

{External systems this repo depends on (services, data stores, queues, third-party APIs) and what
breaks when each is unavailable. Interfaces consumed from other repos belong here; link to
[interfaces.md](interfaces.md) rather than duplicating details.}
