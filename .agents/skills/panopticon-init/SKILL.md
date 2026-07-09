---
name: panopticon-init
description: >-
  Orchestrate Panopticon repo initialization end to end: interface naming, interface extraction,
  documentation generation, then finalization — in the correct dependency order, resuming from a
  checkpoint log if a prior run was interrupted. Apply when the user invokes /panopticon-init,
  right after the bootstrap installer script has printed its prompt, or whenever a full
  initialization (rather than a single step) is requested.
---

# Panopticon init orchestration

Runs the three Phase 2 skills and the Phase 3 finalization command in the one order that works,
tracking progress in a checkpoint log so an interrupted run resumes instead of restarting or
skipping ahead of its prerequisites. Each underlying step also stays independently invocable on
its own — this skill only sequences them.

## Step order

1. `panopticon-interface-naming`
2. `panopticon-interface-extraction` — depends on step 1's naming judgments
3. `panopticon-doc-generation` — depends on steps 1–2: the interface-docs layer renders from
   `panopticon/index.json`, which does not exist yet before those steps run
4. Finalization: `python3 -m panopticon.init_repo --instance <instance>` — the last step, run only
   after 1–3 are complete

## Checkpoint log

Maintain `panopticon/.init-log.json` — a JSON list of completed step ids, e.g.:

```json
["interface-naming", "interface-extraction"]
```

- **Before** starting a step, read the log (treat a missing file as an empty list) and skip any
  step already present.
- **After** a step completes, append its id to the log and write it back immediately — before
  moving to the next step. This is what makes a resumed session (with no memory of the prior one)
  pick up correctly instead of restarting from scratch or skipping into a step whose prerequisites
  were never met.
- Once all four steps have completed and `panopticon/config.json` exists, **delete**
  `panopticon/.init-log.json`. A completed initialization has no further use for it.

Step ids: `interface-naming`, `interface-extraction`, `doc-generation`, `finalization`.

## Determining the instance slug

Read `.github/workflows/panopticon-pr.yml` and extract the `owner/repo` portion from its `uses:`
line (`uses: owner/repo/.github/workflows/panopticon-pr.yml@ref`). Never ask the user for the
instance slug — the bootstrap script already wired this file before printing the
`/panopticon-init` prompt.

## Running

For each step in order, skip it if already recorded in the checkpoint log, otherwise:

1. Run the step (invoke the named skill, or the finalization command for step 4).
2. On success, update the checkpoint log.
3. Continue to the next step.

If finalization reports unmet requirements, fix them (the underlying skills remain invocable
individually for this), then re-run finalization — do not delete the checkpoint log until
finalization actually succeeds.
