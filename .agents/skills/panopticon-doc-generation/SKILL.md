---
name: panopticon-doc-generation
description: >-
  Generate or update a child repo's four-layer Panopticon documentation (architecture overview,
  per-component docs, interface docs, operational docs). Apply when initializing a repo for
  Panopticon, when asked to create or refresh Panopticon docs, or when a code change requires the
  docs to be brought back in line — in any agent harness or via the CI runtime.
---

# Panopticon documentation generation

Produce the four documentation layers in the repo's configured documentation location (recorded
as `docs_location` in `panopticon/config.json`; default `docs/`). Regeneration always updates the
existing files **in place** — never create parallel copies, and remove docs and references for
components that no longer exist.

## The four layers

| Layer | File(s) | Written by |
| --- | --- | --- |
| Architecture overview | `architecture.md` | agent, from `assets/architecture-template.md` |
| Per-component docs | `components/<component>.md` | agent, from `assets/component-template.md` |
| Interface docs | `interfaces.md` | **deterministic tooling only** |
| Operational docs | `operations.md` | agent, from `assets/operations-template.md` |

## Rules

1. **Follow the templates.** Every generated file keeps its template's heading structure; fill
   each section or state explicitly why it does not apply. Do not invent extra top-level
   sections.
2. **Never write `interfaces.md` yourself.** It is rendered from the local index so it can never
   disagree with it. After the index changes, run:

   ```bash
   python3 -m panopticon.docs render --repo-name <repo> --index panopticon/index.json --docs-root <docs-location>
   ```

3. **Ground every statement in the code.** Read the source before describing a component; do not
   document intended or planned behavior. If something can't be determined from the repo, say so
   in the doc rather than guessing.
4. **One component doc per real component.** Components are the repo's meaningful deployable or
   logical units (services, workers, CLIs, shared libraries) — not every directory. Name files
   after the component (`components/<kebab-case-name>.md`).
5. **Deleted components lose their docs.** When regenerating, delete `components/<name>.md` for
   removed components and purge references to them from `architecture.md`. The renderer prunes
   automatically when given the current component list:

   ```bash
   python3 -m panopticon.docs render --repo-name <repo> --component api --component worker ...
   ```

6. **Keep the index current first.** Interface changes go into `panopticon/index.json` (see the
   panopticon-index-schema skill and the panopticon-interface-naming skill for canonical names),
   then docs are rendered/updated. Validate before finishing:

   ```bash
   python3 -m panopticon.docs validate --docs-root <docs-location>
   ```
