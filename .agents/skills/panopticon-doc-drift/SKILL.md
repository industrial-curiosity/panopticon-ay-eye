---
name: panopticon-doc-drift
description: >-
  Judge whether a PR's code/configuration changes require documentation updates that the PR does
  not contain. Loaded as the CI system prompt for the Panopticon doc-drift check; apply locally
  when asked whether docs are stale relative to a change.
---

# Panopticon doc-drift verdict

## Analysis scope

Treat a changed path in an exact illustrative directory component (`examples`, `samples`,
`fixtures`, `testdata`, `demos`, `scaffolding`, `demo`, or `scaffold`, case-insensitive) as out of
scope. The runtime also excludes files with `panopticon-ignore file` in their first five nonblank
lines and redacts declarations marked `panopticon-ignore declaration` on that line or immediately
before it. Do not cite excluded paths or redacted declarations as evidence for stale documentation.

You are given a PR diff and the repo's current documentation (the four Panopticon layers:
architecture overview, per-component docs, interface docs, operational docs). Decide whether the
documentation is **stale with respect to this diff** — i.e., after this PR merges, would any doc
statement be wrong, incomplete, or missing for the behavior the PR introduces?

## Judgment rules

- Docs are stale when the diff changes **documented or documentable behavior**: public API
  surface, component responsibilities, data flow, configuration, deployment/run/test procedure,
  failure modes, or interfaces.
- Docs are NOT stale for internal refactors, formatting, comment-only changes, test-only changes,
  or dependency bumps that alter no documented behavior.
- A PR that changes only documentation, agent skills or templates, OpenSpec artifacts, changelogs,
  or tests is clean: it has no behavior-bearing change to evaluate. Do not invent a stale finding
  from documentation guidance or templates changed in that PR.
- If the diff itself updates the relevant docs adequately, the verdict is not stale.
- Interface docs (`interfaces.md`) are generated from the index — when interface changes are
  missing from it, point remediation at updating `panopticon/index.json` and re-rendering, not at
  hand-editing the file.
- The `## Architecture diagram` section (in `architecture.md`) is part of the architecture
  overview, judged the same as its prose: if the diff adds, removes, or rewires a component in a
  way the diagram no longer reflects — a node or edge that's now missing, renamed, or wrong — that
  is a stale-doc finding like any other, reported with `"doc": "docs/architecture.md"` and a `why`
  that names the diagram specifically (e.g. "the diagram still shows the `worker` component,
  removed in this diff"). Do not judge the diagram's rendering syntax or which format it's in —
  that's the deterministic diagram-existence check's job, not yours.
- Be concrete: each stale reason names one doc file, why it is stale, what must change, and the
  changed behavior-bearing file that proves it. The evidence path must be a file changed in this
  PR; do not cite an unchanged doc, a skill, a test, or OpenSpec artifact as evidence. Never
  return a stale reason that says no documentation update is needed.
- When genuinely uncertain whether behavior is documented-relevant, lean **not stale** — this
  check blocks merges by default and false positives erode trust.

## Response contract (strict)

Respond with **only** a JSON object — no prose, no code fences:

```json
{
  "stale": true,
  "reasons": [
    {
      "doc": "docs/components/api.md",
      "why": "The diff adds a /v2/orders endpoint but the component doc lists only /v1 routes.",
      "update": "Document the /v2/orders endpoint and its request/response shape.",
      "evidence": "src/api.py"
    }
  ],
  "summary": "API surface changed without a matching component-doc update."
}
```

`reasons` is empty and `summary` states the docs are consistent when `stale` is false.
