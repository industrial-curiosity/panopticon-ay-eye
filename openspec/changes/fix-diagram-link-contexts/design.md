## Context

Panopticon authors a child repository's documentation once, then mirrors it to
`docs/{repo}/` in the instance repository. Links between documents in that
child documentation tree remain valid in both locations when they are authored
relative to the document that contains them. A relative link from a child
architecture document to the instance's org diagram cannot have that property:
the two locations have different parents. The current generated back-link is
therefore valid only after mirroring and broken in the child repository.

The existing `panopticon.org_diagram_link` module already resolves the
instance, its default branch, and the child repository anchor into a direct
GitHub URL. The org diagram itself remains at `docs/architecture.md` in the
instance repository and can continue to link to mirrored child docs relatively.

## Goals / Non-Goals

**Goals:**

- Make all navigation within a child documentation tree use document-relative
  paths that work in both the child and mirrored instance locations.
- Make every child-to-org-diagram link a direct, anchored GitHub URL generated
  by the existing resolver.
- Align the generation guidance, template, setup guidance, and regression
  coverage with that division of responsibility.

**Non-Goals:**

- Change the child-to-instance mirroring layout or org diagram rendering.
- Change how the default branch is resolved by `panopticon.org_diagram_link`.
- Add diagram-native click directives or make a remote GitHub lookup mandatory
  when config already contains the resolved branch.

## Decisions

### Preserve relative links for child-local navigation

Links from child architecture documents to component and interface documents
will be authored relative to their containing document. This is the only form
that preserves a link across both directory layouts. The instance org diagram's
links to its mirrored child documents also remain relative to the org diagram,
because they share one instance repository tree.

### Use the existing absolute URL resolver for child-to-org navigation

The architecture template and documentation-generation instructions will obtain
the org-diagram link by running `python3 -m panopticon.org_diagram_link` and
will use its output verbatim. This avoids duplicating the configuration-first
branch resolution and failure behavior. It replaces the current
`../architecture.md#{repo}` form, which is location-dependent.

### Treat link intent as a documentation contract

The architecture-diagrams specification will explicitly distinguish local
relative navigation from child-to-org absolute navigation. User-facing setup
guidance will describe the resulting links without explaining internal retry or
implementation mechanics. Tests will protect the template and guidance from
reintroducing a location-dependent org link.

## Risks / Trade-offs

- An absolute org URL points at the configured default branch rather than an
  unmerged child branch → this deliberately provides a stable org-wide view;
  branch-specific review remains outside the link contract.
- The resolver can fail if required configuration is unavailable → generation
  stops with the resolver's existing actionable error instead of emitting a
  broken or guessed URL.
- Skill guidance and templates can drift → keep the rule in the canonical spec
  and add targeted regression coverage.

## Migration Plan

Update the documentation-generation skill and architecture template, then
regenerate affected child architecture documents so their org-diagram links are
absolute. Existing relative links inside child documentation remain unchanged.
No data migration or rollback procedure is required; reverting the changed
guidance restores the prior generated form.

## Open Questions

None.
