# Surface organization interface conflicts

## Why

The organization diagram currently renders conflicts no differently from clean
interfaces, and same-name interfaces of different types can coexist without any
visible warning. Maintainers need the organization architecture document to make
confirmed conflicts and deterministic potential name collisions immediately
obvious.

## What Changes

- Detect a potential name collision when same-name interface objects of
  different types involve disjoint repository sets.
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
documentation.
