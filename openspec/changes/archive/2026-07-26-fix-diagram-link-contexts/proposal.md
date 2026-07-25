# Fix diagram link contexts

## Why

The generated child architecture document currently uses a relative link to the
org diagram that works only after the document is copied into the instance repo.
Users viewing the child repository on GitHub receive a broken link.

## What Changes

- Keep links among a child repository's documentation relative to that document
  tree, so they work in both the child and mirrored instance locations.
- Require links to the org architecture diagram to use its resolved absolute
  GitHub URL, including the child repository anchor.
- Remove documentation that treats a broken child-repository org link as
  expected behavior.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `architecture-diagrams`: distinguish child-document-relative navigation from
  absolute navigation to the org architecture diagram.

## Impact

The documentation-generation skill and architecture template, architecture
diagram specification, setup guidance, and diagram-link regression coverage are
affected. No new dependency or external API is required.

