# Design: template sync branch selection and doc-drift diagnostics

## Context

The instance's fixed `Sync from template` caller invokes a shared workflow that
fetches and merges the public template's `main` branch. This prevents an
instance branch from exercising a proposed template branch. The shared
workflow also does not summarize the paths affected by a merge.

Doc drift already plans and evaluates isolated batches, but its only output is
the final report. An Actions operator cannot see the retained paths, selected
batch membership, or progress through evaluations while keeping the PR report
focused on the final result.

## Goals / Non-Goals

**Goals:**

- Let a workflow-dispatch user select a non-empty named template ref, defaulting
  to `main`.
- Use the selected ref consistently for fetch, merge, recovery text, and
  summary output.
- Summarize changed paths after a successful template merge.
- Emit safe batch-planning and evaluation progress in Actions step logs for all
  provider workflows.

**Non-Goals:**

- Selecting a template repository, tag policy, or arbitrary Git revision.
- Changing protected-path merge behavior, sync authentication, or push policy.
- Adding debug details to the Actions summary or PR comment.
- Logging prompt, response, endpoint, credential, or diff contents.

## Decisions

### Expose one optional `template_ref` workflow input

The instance caller exposes a `workflow_dispatch` string input with `main` as
its default and passes it to a compatible optional input on the shared
reusable workflow. The shared workflow validates that the ref is non-empty,
fetches it as the template remote-tracking ref, and merges that fetched ref.
Existing callers remain compatible because the reusable input has a default.

Using a ref rather than a separate workflow preserves a single sync path and
lets a maintainer dispatch from an instance test branch. Allowing arbitrary
template repositories or ref expressions is out of scope because it would
expand the trusted sync source beyond the template repository.

### Diff against the recorded pre-sync SHA for the summary

The shared workflow already records `PANOPTICON_SYNC_START_SHA` before the
fetch. After a successful merge, it will compute the changed paths from that
SHA to `HEAD` and append a dedicated summary section. An empty list explicitly
states that the selected ref introduced no changes. This reports the actual
post-merge tree delta, including protected-path outcomes, rather than merely
listing files in the incoming template commit.

### Add explicit, safe debug events to the drift CLI

`panopticon.drift` will gain an opt-in debug flag. It will write short
structured human-readable progress lines to stdout: the retained path names,
planner start and validated result, per-batch path/doc assignment, and
evaluation start/completion with safe request diagnostics. It will not print
diff, documentation, prompts, model responses, endpoints, environment values,
or credentials.

Each built-in provider workflow passes the flag so the information remains in
the doc-drift step log. The normal final report remains unchanged in purpose:
it reports the verdict and remediation, not execution tracing.

## Risks / Trade-offs

- [A malformed or absent ref could make fetch confusing] → Validate the input
  before fetching and report the selected ref in the failure summary.
- [Template branch names can contain shell-sensitive characters] → Pass the
  value as a quoted argument and avoid shell evaluation of it.
- [Debug logging can disclose sensitive input] → Limit events to path names,
  batch membership, stage names, and existing safe request diagnostics.
- [Three provider workflows can drift] → Apply the same invocation and cover
  all workflow variants with contract tests.

## Migration Plan

1. Merge the template change.
2. Sync an instance normally; existing callers use `main` by default.
3. To test a template branch, dispatch `Sync from template` from the intended
   instance branch and set `template_ref` to the template branch name.
4. If a branch sync fails, use the recovery instructions, which name the same
   selected ref.
5. Roll back by reverting the template change; existing instance callers stay
   dispatch-compatible through the reusable workflow default.

## Open Questions

None.
