# Evidence-backed doc-drift design

## Context

The doc-drift check currently gives an LLM the complete PR diff and all child
documentation, then accepts any JSON-shaped verdict. In PR #6, the diff changed
the generation guidance and changed `docs/architecture.md` from a relative to an
absolute org-diagram link. The LLM nevertheless reported that architecture
document stale and also returned a stale reason whose own text said no component
document update was needed.

## Goals / Non-Goals

**Goals:**

- Prevent documentation-only, template-guidance, test-only, and specification-
  only diffs from producing child documentation drift findings.
- Require stale findings to be actionable, internally consistent, and tied to a
  behavior-bearing change in the PR.
- Preserve LLM judgment for code and configuration changes where deterministic
  comparison cannot establish documentation adequacy.

**Non-Goals:**

- Replace the LLM doc-drift judge with a general deterministic documentation
  analyzer.
- Require regeneration whenever documentation-generation guidance changes.
- Change index-currency or diagram-existence checks.

## Decisions

### Classify diffs before invoking the LLM

The check will classify changed paths into behavior-bearing inputs and
documentation-only inputs. When a PR has no behavior-bearing change, doc-drift
will return a clean verdict without calling the LLM. Child docs, agent skills,
OpenSpec artifacts, changelogs, and tests alone do not constitute a behavior-
bearing change; source, runtime configuration, and workflow changes remain
eligible inputs.

This directly handles template and generation-guidance changes without teaching
the LLM to infer a nonexistent child behavior change.

### Make stale verdicts evidence-bearing

For behavior-bearing diffs, the LLM response will include a non-empty evidence
reference for every stale reason, identifying the changed behavior-bearing file
that necessitates the cited documentation update. The deterministic validator
will reject malformed, empty, contradictory, or untraceable stale findings as
an operational failure rather than return exit code 2.

The prompt will explicitly require a clean verdict when the PR's changed docs
already cover the behavior, and prohibit a stale reason whose update says no
update is required.

### Keep workflow handling unchanged for validated business verdicts

Provider workflows already distinguish exit code 2 from operational failures.
The refined validation will use the existing operational-failure path for an
invalid LLM verdict, so no provider-specific gating behavior changes.

## Risks / Trade-offs

- A path classifier may omit an unusual behavior-bearing file → keep the
  classifier narrow only for clearly non-behavior classes and cover known
  runtime configuration and workflow paths with tests.
- The LLM can still make an evidence-backed semantic mistake → stronger prompt
  instructions and evidence requirements reduce this risk without pretending to
  solve arbitrary documentation semantics deterministically.
- An invalid response fails the check rather than passing it → this is safer
  than incorrectly blocking a merge for stale docs, while preserving a visible
  operational failure for maintainers to correct.

## Migration Plan

Ship the classifier, verdict schema validation, skill wording, and tests together
in the shared tooling. Child repositories receive the behavior through their
configured workflow reference or normal tooling refresh. No data migration is
required.

## Open Questions

None.
