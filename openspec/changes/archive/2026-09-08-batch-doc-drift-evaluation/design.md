# Design: batch doc-drift evaluation

## Context

Doc drift currently constructs one prompt from every behavior-bearing patch and
its selected documentation context. A PR that mostly changes Panopticon-managed
resources can therefore make a large request despite not changing the child
repository's documented behavior. When that request times out, the existing
report exposes transport facts but not the concrete ways to reduce the request
or raise its budget.

## Goals / Non-Goals

**Goals:**

- Exclude managed repository metadata deterministically before LLM input.
- Isolate every product doc-drift evaluation to the smallest LLM-planned batch.
- Preserve coverage for large product changes without sending one monolithic
  patch or irrelevant documentation to the evaluator.
- Make planning and evaluation timeouts immediately actionable.

**Non-Goals:**

- Change the configured provider, transport retry policy, or workflow contract.
- Automatically split a timed-out evaluation batch and retry it.
- Ask the LLM to judge managed Panopticon metadata or documentation-only work.

## Decisions

### Deterministic scope precedes LLM planning

`panopticon/`, `.github/`, and `.agents/` are child-repository metadata for
doc drift and are excluded alongside existing documentation, tests, OpenSpec,
and analysis-scope exclusions. The classifier remains deterministic because
whether a path is managed metadata is structural, not a judgment task.

### Use a dedicated structured batch-planning prompt for every relevant PR

The planner receives only retained changed paths and available documentation
paths. It returns strict JSON batches. Each retained changed path appears once;
each batch contains the smallest coherent set of changed paths and only the
documentation paths needed to judge them. A dedicated planning skill separates
the planner's path-assignment contract from the evaluator's stale-document
judgment contract.

Always planning avoids context pollution and makes small and large PRs follow
the same predictable execution model. A deterministic fixed-size chunker was
rejected because it cannot know which files jointly implement one behavior or
which documentation applies.

### Evaluate batches independently and aggregate verified results

The evaluator receives only a planned batch's patch and documentation contents.
Its stale reasons must cite a changed path from that batch. Clean results are
discarded after diagnostics are collected; stale reasons are combined into the
existing doc-drift report and remediation actions are deduplicated. This keeps
the existing workflow exit-code and final-gate behavior intact.

### Fail immediately on planning or evaluation timeout

Planning and each evaluation use the existing provider-neutral LLM client and
its configured attempts. If either exhausts those attempts, doc drift writes
one operational-failure report and returns its existing operational-failure
exit code; it does not split or retry a batch. The report identifies whether
planning or a named evaluation batch failed, lists safe path names and byte
counts, and recommends reducing/splitting the PR or increasing the effective
`PANOPTICON_LLM_TIMEOUT_SECONDS` within its supported range.

## Risks / Trade-offs

- [The planner can return an invalid batch assignment] → Strictly validate that
  every retained path appears exactly once and every named document exists;
  treat invalid output as an operational failure.
- [One additional LLM request adds latency] → The planner has path lists only,
  while each evaluator receives much less context than the current monolithic
  prompt.
- [A timeout still blocks the PR] → This is intentional: silently retrying or
  splitting could obscure provider limits and make evaluation nondeterministic.
- [A planner groups paths imperfectly] → Require minimal coherent groups and
  retain per-batch source evidence in every stale reason.

## Migration Plan

1. Release the template and instance workflow changes together.
2. Existing child callers continue to invoke the same reusable workflow; no
   child re-bootstrap is required because the caller ABI and provider inputs do
   not change.
3. Roll back by reverting the template change; existing provider configuration
   and child callers remain valid.

## Open Questions

None.
