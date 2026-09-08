# Template sync branch selection and doc-drift diagnostics

## Why

Instance maintainers need to test template changes before merging them to the
template default branch. The current sync workflow always uses `main`, and
doc-drift runs do not reveal the planner's batches in step logs, making a
failed evaluation difficult to diagnose.

## What Changes

- Add a named template-ref input to the instance template-sync dispatch flow;
  retain `main` as the default.
- Record the selected template ref and every path changed by a successful
  template sync in the Actions job summary.
- Add safe, opt-in doc-drift debug logging that reports detected product paths,
  the planner's selected batches, and evaluation progress without exposing
  request credentials or full prompt content.
- Enable that debug logging in each built-in provider PR workflow, while
  retaining summaries and PR reports for user-facing outcomes only.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `tooling-currency`: Template synchronization can select a named template
  ref and reports its changed paths.
- `batched-doc-drift-evaluation`: Batched evaluations provide safe step-log
  diagnostics that make their planning and execution observable.

## Impact

The change affects the instance sync caller and shared template-sync workflow,
the `panopticon.drift` command, all built-in provider PR workflows, their
workflow and Python tests, and operator documentation for testing a template
branch.
