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

7. **Draw the architecture diagram grounded in the actual code.** The `## Architecture diagram`
   section holds exactly one fenced code block, tagged with the instance's configured diagram
   format (read `panopticon.diagram.config.json` in the instance repo checkout if one is
   available; default `mermaid` when absent or no instance checkout is available locally) —
   depicting this repo's components and how they relate, same "ground every statement in the
   code" discipline as the rest of this layer. Do not invent components or relationships that
   aren't in the code. Directly below the fenced block, add a markdown link back to this repo's
   section in the org diagram: `` [org diagram](../architecture.md#{repo}) ``, where `{repo}` is
   `panopticon/config.json`'s `repo` field (e.g. `repo: "svc-a"` → `[org diagram](../architecture.md#svc-a)`).
   This is a *relative* link, not an absolute GitHub URL — this repo's docs are merged into the
   instance repo at `docs/{repo}/` on every push (master-sync capability), landing this file at
   `docs/{repo}/architecture.md` alongside the org diagram at `docs/architecture.md`, so
   `../architecture.md` resolves correctly there. It will not resolve when viewed directly in this
   repo before that merge — that's expected: architecture diagrams are reviewed in the instance
   repo, not by browsing child repos in isolation. No node-level click-through inside the diagram —
   GitHub's Mermaid renderer does not reliably support `click`-to-URL navigation; the back-link is a
   plain markdown link, not a diagram directive.
8. **Write the README architecture links.** At the top of `README.md`, write or refresh two markdown
   links, own-repo diagram directly above the org diagram, both labeled with the repo name (never a
   bare "architecture" — ambiguous once two links sit stacked):

   ```markdown
   [{repo} architecture]({docs_location}/architecture.md)
   [org architecture](<output of the command below>)
   ```

   The first is a relative link built from `panopticon/config.json`'s `repo` and `docs_location`
   fields; like the diagram-section back-link (rule 7), it resolves once this repo's docs are merged
   into the instance repo, not necessarily before. The second is a fully-qualified GitHub URL — run:

   ```bash
   python3 -m panopticon.org_diagram_link
   ```

   and use its printed line verbatim. Do not re-derive the URL or its fallback behavior yourself: the
   script already implements the correct config-first, live-lookup-fallback, fail-loudly-never-guess
   logic (architecture-diagrams capability, "Org-diagram link script"). If the script exits non-zero,
   stop and report the error it printed rather than writing a partial or guessed link.
9. **Resolve drift against docs you find, don't just flag it.** If existing documentation — this
   repo's own docs, or a reference/fixture doc committed elsewhere in the repo — describes code,
   configuration, or interfaces that no longer match the repo's actual current state, revise the
   documentation to match reality rather than leaving it stale or merely noting the mismatch in a
   report. Do not call out the resolution inline in the revised text. Instead, append an entry to
   `panopticon-changelog.md` in the docs location (create it if absent) naming the doc, what was
   found, and how it was resolved, so maintainers can see Panopticon found and fixed it without
   digging through history. This changelog file is an ordinary generated file — never stage,
   commit, or push it yourself; leave it for the user to keep, edit, or discard at their own commit
   step, same as every other file initialization produces. If you can't tell how to resolve the
   mismatch from the repo alone — the documented work looks intentional but was never finished, or
   the signals genuinely conflict — stop and ask the user rather than guessing at intent. This does
   not apply to the CI doc-drift check (panopticon-doc-drift skill): that check only reports a
   verdict on a PR diff and never edits docs.
