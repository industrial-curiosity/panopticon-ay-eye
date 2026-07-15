## 1. Update the panopticon-init skill

- [x] 1.1 Update "Step order" in `.agents/skills/panopticon-init/SKILL.md` to six steps: insert
      `panopticon-dependency-naming` (step 3) and `panopticon-dependency-extraction` (step 4)
      between `panopticon-interface-extraction` and `panopticon-doc-generation`, renumbering
      doc-generation to step 5 and finalization to step 6.
- [x] 1.2 Update the "Checkpoint log" section's example JSON and "Step ids" list to include
      `dependency-naming` and `dependency-extraction` in the correct position.
- [x] 1.3 Review the "Running" and "Determining the instance slug" sections for any step-count or
      step-name references that need updating — found and fixed a stale "step 4" reference to the
      finalization command (now step 6); the drift-resolution cross-reference correctly stays
      scoped to doc-generation/interface-naming since the dependency skills resolve ambiguity by
      leaving cases unreported rather than stopping to ask the user.

## 2. Update the repo-initialization spec

- [x] 2.1 Apply the `specs/repo-initialization/spec.md` delta in this change to
      `openspec/specs/repo-initialization/spec.md` — "Orchestrating init skill" (six-step order,
      six recognized checkpoint-log step ids, updated/added scenarios) and "Agent-driven
      initialization" (Phase 2 description names all five agent-driven skills).
- [x] 2.2 Re-read the full updated "Orchestrating init skill" requirement once merged to confirm
      no scenario still references "four steps" or omits the two new skills — grepped the merged
      spec and confirmed clean; the only remaining "four steps" mentions repo-wide are in this
      change's own proposal/design (describing the prior state, correctly) and in
      `docs/action-plans/init-dependency-steps.md` (handled by task 4.2).

## 3. Verify end to end

- [ ] 3.1 Run `/panopticon-init` (or the project's equivalent test harness) against a fixture repo
      that has at least one real internal (same-org) dependency, and confirm
      `dependencies/{repo}.json` is populated before doc-generation runs.
      Deferred (user decision, 2026-07-15): no fixture child+instance repo pair with a genuine
      internal dependency exists in this workspace, and this is a live agent-driven flow with no
      Python test harness (orchestration is agent-followed `SKILL.md` instructions, not code).
      Left as a manual follow-up: verify against a real org repo the next time one is initialized
      through `/panopticon-init` after this change ships.
- [ ] 3.2 Confirm generated docs and the org diagram reflect the dependency edges with no manual
      step beyond the standard `/panopticon-init` invocation.
      Deferred alongside 3.1, same reason — verify together on the same real initialization run.
- [x] 3.3 Simulate an interrupted run: stop after `dependency-naming` completes and confirm a
      fresh agent session resumes at `dependency-extraction`, not re-running `dependency-naming`
      or skipping to `doc-generation` — traced the documented "Running" algorithm (skip any step
      already in the log, in order) against a log of
      `["interface-naming", "interface-extraction", "dependency-naming"]`: steps 1–3 are skipped,
      step 4 (`dependency-extraction`) runs next. Matches the spec's "Resuming after an
      interrupted session" scenario exactly.
- [x] 3.4 Confirm `panopticon/.init-log.json` is deleted only after all six steps (including the
      two new ones) have completed and `panopticon/config.json` is written — verified directly in
      the updated "Checkpoint log" section text: "Once all six steps have completed... delete
      panopticon/.init-log.json."

## 4. Documentation

- [x] 4.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes
      introduced by this change — README.md's skills-directory summary (lines 165-169) grouped
      `panopticon-dependency-naming`/`panopticon-dependency-extraction` with the standalone
      CI-check skills rather than the `panopticon-init`-orchestrated ones; corrected. No
      `docs/spec.md` exists in this repo (specs live under `openspec/specs/`, updated in task 2.1).
- [x] 4.2 Mark `docs/action-plans/init-dependency-steps.md` as implemented (or remove it) once
      this change is archived, since its content is now superseded by the archived spec delta —
      added a status banner pointing at this archived change and the CHANGELOG entry, kept the
      file for its reasoning trail. Also removed the now-completed bullet from
      `docs/planned-work.md`'s backlog.
