# Organization interface-conflict visibility design

## Context

The compiled interface index already owns conflict state, but the generated
organization architecture document renders all interface resources as healthy.
It also lacks a conflict for same-name objects with different types that belong
to disjoint repository sets. Child architecture documents remain agent-authored
and are intentionally outside this change.

## Goals / Non-Goals

**Goals:**

- Detect deterministic potential same-name/type-mismatch collisions during the
  existing compiled-index rebuild.
- Make confirmed and potential conflicts prominent in the generated organization
  architecture document.
- Emphasize every affected resource in Mermaid and its relationship table.
- Preserve deterministic merge/simulation parity and index round trips.

**Non-Goals:**

- Edit child-repository architecture documents or their mirrored copies.
- Decide whether a potential collision is a true semantic collision.
- Change organization conflict-gating defaults or introduce an LLM call.

## Decisions

### D1: Detect potential collisions from the compiled structural view

After folding entries by `(name, type)`, group the resulting interface objects
by name. When two or more types under one name have disjoint participating-repo
sets, emit one deterministic `potential-name-collision` conflict for that name.
The details name every involved type and repository. Overlapping repository sets
remain unflagged, preserving the established type-migration shape.

The conflict uses the existing compiled-only `conflicts` array with a dedicated
sentinel type for a multi-type finding. Reconstruction of shard ownership
continues to use claims only for ownership conflicts; the potential collision is
recomputed from current shards on every rebuild.

Alternative considered: treat all same-name/different-type objects as conflicts.
Rejected because it makes normal type migrations noisy and obscures the more
useful potential-collision signal.

### D2: Derive visual conflict targets from compiled conflicts

The organization renderer derives targets from the compiled `conflicts` array:
ordinary conflicts target their exact `(name, type)`, while a multi-type
potential collision targets every interface object under its name. This keeps
the rendered document a pure function of the compiled index and guarantees it
cannot diverge from merge reports.

### D3: Use Mermaid resource nodes for visible red emphasis

Healthy interfaces remain edge labels. For an affected resource, render a
dedicated Mermaid resource node between the participating repositories and
apply a `classDef` with a red stroke/text and bold font. This is more reliable
than attempting to style an edge label, which Mermaid does not expose as a
stable target.

Relationship-table resource names use a red-circle indicator and bold Markdown
(`🔴 **name**`). This is visible in GitHub's Markdown renderer without relying
on unsupported HTML or CSS styling.

### D4: Render one organization-only conflict summary

Immediately after the organization document title, render `## Detected
interface conflicts` when the compiled index has any interface conflicts. Each
item identifies its name, type or involved types, reason, details, and affected
repositories. Omit the heading entirely when no interface conflicts exist.

Alternative considered: add a status block to each child architecture document.
Rejected because those files are child-owned and copied before the compiled
organization conflict set is known.

## Risks / Trade-offs

- A disjoint-repository mismatch is a potential collision, not proof of one →
  preserve advisory semantics and label the reason as potential.
- Mermaid styles vary by renderer → use standard `classDef` syntax and retain
  the text/table indicator as an accessible fallback.
- One name can generate several mismatch pairs → emit one deterministic finding
  per name and list all involved types and repositories.

## Migration Plan

1. Extend schema validation and deterministic compilation for the new conflict
   reason.
2. Extend the organization renderer and its tests.
3. Existing compiled indexes remain valid; their next rebuild adds any detected
   potential findings and regenerates the organization document.
4. Rollback removes the renderer/compiler change; a subsequent rebuild removes
   derived potential-collision entries.

## Open Questions

None.
