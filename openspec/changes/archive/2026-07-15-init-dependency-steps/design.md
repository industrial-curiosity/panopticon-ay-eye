## Context

`panopticon-init` (`.agents/skills/panopticon-init/SKILL.md`) sequences four skills today:
`panopticon-interface-naming` → `panopticon-interface-extraction` → `panopticon-doc-generation` →
finalization (`python3 -m panopticon.init_repo`), tracked via a checkpoint log
(`panopticon/.init-log.json`) so an interrupted run resumes correctly in a new agent session with
no memory of the prior one. The `dependency-indexing` capability and its two skills
(`panopticon-dependency-naming`, `panopticon-dependency-extraction`) already exist and are fully
specified, but nothing calls them during initialization — every freshly initialized repo has an
empty dependency index.

## Goals / Non-Goals

**Goals:**
- Wire `panopticon-dependency-naming` and `panopticon-dependency-extraction` into the init
  sequence so a fresh `/panopticon-init` run produces a populated dependency index alongside the
  interface index.
- Preserve the checkpoint/resume guarantee across the now six-step sequence.
- Keep every skill independently invocable on its own, unchanged from today.

**Non-Goals:**
- No change to the `dependency-indexing` capability itself (schema, detection layers, hint forms) —
  both skills are already fully specified; this change only adds a call site.
- No change to `panopticon/init_repo.py` finalization validation — it validates the four
  documentation layers (architecture overview, per-component, interface, operational) and index
  schema-validity generically, and doesn't need to know the step count that produced them.
- No backward-compatibility shim for checkpoint logs written by the old four-step version
  mid-flight (see Risks below) — this is pre-1.0 template tooling with no external checkpoint-log
  compatibility guarantee stated anywhere in the existing spec.

## Decisions

**Ordering: dependency steps between interface-extraction and doc-generation, not after.**
`panopticon-dependency-naming`'s own description states a `panopticon-dependency-of` hint links a
dependency entry to an *existing* interface's canonical name — so the interface index
(`panopticon/index.json`) must be built first, which interface-extraction (step 2) produces.
Doc-generation (step 5 in the new order) renders from compiled indices; running it before the
dependency steps would mean the first generated docs are missing dependency edges, the same
class of gap this change exists to close. Placing the two new steps at positions 3–4 (between
extraction and doc-generation) is therefore the only ordering that satisfies both constraints
simultaneously — this mirrors exactly how `lessons-learned.md`'s own suggested fix reasoned about
placement, verified independently against the two dependency skills' descriptions
(`.agents/skills/panopticon-dependency-naming/SKILL.md`,
`.agents/skills/panopticon-dependency-extraction/SKILL.md`).

**Two separate steps (naming, then extraction), not one combined step.** This mirrors the existing
interface-naming/interface-extraction split exactly: naming establishes judgment/hint conventions
that extraction then applies, and keeping them separate lets a checkpoint log resume between them
rather than re-running a combined step from scratch. Consistency with the existing four-step
pattern outweighs any argument for collapsing them.

**Checkpoint log gets two new step ids, not a schema version bump.** `panopticon/.init-log.json`
is a flat JSON list of completed step ids (`interface-naming`, `interface-extraction`,
`doc-generation`, `finalization` today). Adding `dependency-naming` and `dependency-extraction` to
the recognized set is additive — no format change, just two new possible list entries.

## Risks / Trade-offs

- **[Risk]** A checkpoint log from an in-flight init run started under the old four-step skill
  version, if resumed after this change lands, has no record of dependency steps and no way to
  distinguish "dependency steps not yet run" from "dependency steps don't apply to this run" →
  **Mitigation**: none needed beyond documentation — `panopticon-init` runs are short-lived
  (minutes, within one bootstrap session) and the checkpoint log's own stated purpose is surviving
  an interrupted *agent session*, not surviving a *skill version upgrade* mid-run. No scenario in
  the existing spec commits to that broader guarantee. If it proves to matter in practice, the fix
  is a one-line note in `panopticon-init`'s resume instructions to treat a log missing the new
  step ids as pre-upgrade and restart from `dependency-naming`, not a schema change.
- **[Risk]** If a repo has zero internal (same-org) dependencies, `dependency-extraction` finding
  nothing to record could be mistaken for the step having failed to run → **Mitigation**: this is
  already the correct, expected outcome per the `dependency-indexing` capability (empty entries are
  legitimately removed/absent) — the checkpoint log records the step as *completed*, not that it
  *found* dependencies, exactly the same way `interface-extraction` completing with zero new
  interfaces is already unremarkable today.

## Migration Plan

No data migration. This changes an orchestration skill and its spec; existing initialized repos
(`panopticon/config.json` already written) are unaffected — the new steps only run during
`/panopticon-init`, which a fully initialized repo has no reason to re-invoke.
