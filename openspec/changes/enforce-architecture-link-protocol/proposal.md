# Enforce architecture link protocol

## Why

The README architecture link was corrected, but a generated child architecture
document can still retain an incompatible link. Every architecture-navigation
link needs one explicit protocol so it works in both a child repository and its
mirrored instance documentation.

## What Changes

- Require all generated child architecture navigation links to use the
  context-appropriate protocol.
- Require the child architecture overview's org-diagram back-link to use the
  resolver-produced absolute URL, not a relative child-repository path.
- Add regression coverage for the README, child architecture template, and
  generation guidance together.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `architecture-diagrams`: Define and enforce the complete link protocol for
  generated child and organization architecture navigation.

## Impact

- `.agents/skills/panopticon-doc-generation/` guidance and architecture template
- Architecture-link regression tests and testing documentation
- README and technical architecture documentation
