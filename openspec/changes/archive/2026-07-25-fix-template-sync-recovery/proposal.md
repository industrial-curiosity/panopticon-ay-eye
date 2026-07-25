# Fix template sync recovery

## Why

The shared template-sync workflow writes literal `\n` sequences into runtime
Git attributes and the step summary. This prevents intended merge protection
from being registered and leaves maintainers with malformed, generic recovery
instructions that do not identify the failed operation.

## What Changes

- Write valid newline-delimited runtime Git attributes for generated and
  org-declared protected paths, including the local recovery commands.
- Preserve instance-owned generated files when both the instance and template
  change them during a template sync.
- Make failure summaries render as Markdown and identify the failed sync stage,
  detected error, and relevant recovery action.
- Add tests that execute or inspect the workflow source closely enough to catch
  escaping regressions in runtime attributes and summaries.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: Template synchronization must register effective
  protected-path attributes and provide actionable, correctly rendered failure
  recovery.

## Impact

- `.github/workflows/shared-template-sync-caller-only.yml`
- `tests/test_sync_from_template.py`
- Template-sync requirements and setup guidance, if the user-visible recovery
  contract changes
