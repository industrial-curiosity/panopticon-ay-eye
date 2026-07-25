# Template sync recovery design

## Context

The shared template-sync workflow creates runtime Git attributes for paths that
must retain the instance version. Its Python string literals currently encode
literal backslash-n characters, so Git does not receive valid line-delimited
`merge=ours` entries. The same escaping defect makes the Actions summary render
as opaque text. A generic post-failure recovery block then omits the failed
stage and its Git error.

## Goals / Non-Goals

**Goals:**

- Register generated and org-declared protected paths with effective Git
  attributes before merging.
- Preserve an instance-owned generated architecture document when both sides
  modify it.
- Give maintainers valid Markdown that identifies the failed stage, its error,
  and the relevant local recovery path.
- Prevent a regression through workflow-source and real-Git tests.

**Non-Goals:**

- Change template-sync authentication, the fixed template source, or normal
  merge policy for unprotected files.
- Automatically resolve genuine conflicts outside protected paths.

## Decisions

### Use real newline characters in runtime Python strings

The workflow and recovery heredoc will write a physical
`<path> merge=ours` line for every protected path. This is the smallest change
that makes Git select the already configured `ours` driver. A tracked
`.gitattributes` file remains unsuitable because protection is instance-local
and may contain organization-specific paths.

### Report failure at the stage that detects it

Each failure-prone sync stage will write its own concise Markdown summary before
exiting. The summary will name the stage and include the detected Git or command
error, then link it to local recovery where applicable. The final recovery block
will provide commands but will not be the only explanation of a failure.

### Test the workflow source as well as merge behavior

Existing real-Git tests model correct attributes but do not verify that the
workflow emits them. Add source-level assertions for newline escaping and
summary rendering, while retaining integration coverage for both-sided changes
to protected paths.

## Risks / Trade-offs

- [Failure output could be noisy] → Include only the detected command error in
  the step summary and keep the full log available in the failing step.
- [Workflow edits can be copied into old instances] → The fixed minimal caller
  already references the template-owned reusable workflow at `main`, so the
  next run consumes the repair.
- [Source assertions can become implementation-sensitive] → Assert the newline
  and failure-summary contract without pinning unrelated workflow formatting.

## Migration Plan

1. Update the shared reusable workflow and its tests in the template.
2. Update user-facing recovery documentation if its instructions change.
3. Trigger template sync in a representative instance; no instance caller
   migration is required.
