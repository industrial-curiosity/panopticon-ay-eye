# Preserve the Instance Org Diagram During Template Sync

## Why

`docs/architecture.md` is shipped by the template as a useful empty-state
placeholder but becomes deterministic, instance-owned generated output as soon
as the instance builds its org diagram. Template sync must preserve that
generated instance content when both histories contain or modify the path, while
still installing the placeholder into an instance that does not have the file
yet.

## What Changes

- Register `docs/architecture.md merge=ours` in `.git/info/attributes` before
  every template merge.
- Reuse the workflow's existing `merge.ours.driver true` configuration.
- Treat the path as a template-declared, instance-owned generated path with its
  own fixed sync rule.
- Keep it separate from the protected JSON configuration registry and from
  org-declared `protected_paths` customizations.
- Add real-git integration coverage for independent additions, independent
  modifications, unrelated histories, and placeholder installation when the
  instance lacks the path.
- Document the generated-path rule and its distinction from customization and
  protected configuration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: Extend the template update workflow's pre-merge
  attribute registration and merge behavior for the fixed generated org-diagram
  path.
- `architecture-diagrams`: Define how the template placeholder transitions to
  instance-owned generated content during template sync.

## Impact

- Affects `.github/workflows/sync-from-template.yml` and its real-git
  integration tests.
- Updates sync documentation and the architecture-diagram contract.
- Does not change `panopticon.config.json`, `PROTECTED_CONFIG_FILES`, tracked
  `.gitattributes`, or org customization semantics.
- Adds no dependency and no new merge driver.
