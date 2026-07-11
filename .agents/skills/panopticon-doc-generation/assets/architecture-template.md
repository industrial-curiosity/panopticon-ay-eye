# {Repo name} — architecture overview

## Purpose

{One or two paragraphs: what this repo exists to do, for whom, and the problem it solves.}

## Components

{One bullet per component, linking to its per-component doc:}

- [{component-name}](components/{component-name}.md) — {one-line responsibility}

## Architecture diagram

{A single fenced code block, tagged with the instance's configured diagram format (default
`mermaid`), depicting this repo's components and how they relate — grounded in the actual code,
same discipline as the rest of this layer. Directly below the block, a one-line link back to this
repo's section in the org diagram: `See the org diagram: {instance-repo-url}/docs/architecture.md#{repo}`
(derived from `panopticon/config.json`'s `instance` field).}

```mermaid
{diagram content}
```

See the org diagram: {instance-repo-url}/docs/architecture.md#{repo}

## Data flow

{How data moves through the system: entry points, processing stages, storage, outputs. A short
ordered narrative or a text diagram. Name the interfaces involved using their canonical index
names.}

## Dependencies

{External systems this repo depends on (services, data stores, queues, third-party APIs) and what
breaks when each is unavailable. Interfaces consumed from other repos belong here; link to
[interfaces.md](interfaces.md) rather than duplicating details.}
