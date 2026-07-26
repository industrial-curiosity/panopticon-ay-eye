# Surface organization interface conflicts

## Why

The organization diagram currently omits interfaces used or managed by only one
repo, renders conflicts no differently from clean interfaces, and lets
same-name interfaces of different types coexist without a visible warning.
Maintainers need a complete organization interface inventory that makes
confirmed conflicts and deterministic potential name collisions obvious.

## What Changes

- Detect a potential name collision when same-name interface objects of
  different types involve disjoint repository sets.
- Render every participating repo's interface resources in the generated
  organization architecture document, including single-repository resources.
- Render all confirmed and potential interface conflicts only in the generated
  organization architecture document under `## Detected interface conflicts`.
- Highlight every conflicting resource in the organization Mermaid diagrams
  and relationship tables using bold red presentation.
- Leave child-repository architecture documents unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-indexing`: record deterministic potential same-name/type-mismatch
  conflicts in the compiled interface index.
- `architecture-diagrams`: surface and highlight compiled interface conflicts
  in the generated organization architecture document.

## Impact

Changes the compiled interface-conflict schema and deterministic merge/rendering
logic in `panopticon/index.py`, `panopticon/merge.py`, and
`panopticon/diagrams.py`; extends their unit tests and organization-diagram
documentation. This does not create a conflict merely because one repo alone
uses or manages an interface.
