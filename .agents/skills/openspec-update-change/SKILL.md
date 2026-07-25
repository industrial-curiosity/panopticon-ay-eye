---
name: openspec-update-change
description: Update an OpenSpec requirement or scenario whenever a change's specification is added, modified, removed, refined, or repaired, including after a completed but unarchived change was applied from an incorrect spec. Select exactly one unarchived change; reopen it and reset incompatible tasks for reapplication.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.4.1"
---

Update OpenSpec artifacts while keeping canonical specifications, selected change
deltas, implementation tasks, and design decisions aligned.

## Steps

1. **Require exactly one unarchived change**

   Run:

   ```bash
   openspec list --json
   ```

   - Treat every listed, non-archived change as selectable, including a completed
     change whose implementation has already been applied.
   - If no unarchived changes exist, report that update requires an unarchived change
     and STOP.
   - If multiple unarchived changes exist, prompt the user to select one and STOP.
   - If exactly one unarchived change exists, update that change immediately;
     do not ask the user to reopen it, create a follow-up change, or choose it.

2. **Identify the capability and requested change**

   Use a named capability when supplied. Otherwise, infer it from the
   conversation or inspect `openspec/specs/` and ask the user only if the
   target remains ambiguous. State the selected capability and whether the
   work adds, modifies, or removes requirements.

3. **Resolve the planning context**

   Resolve paths from `openspec status --change "<change-name>" --json`; do not
   assume a repository-local change path when the CLI provides planning-home
   paths. Write a delta spec for the selected change. Do not update a
   canonical spec directly through this skill.

4. **Read before writing**

   Read the canonical spec and, for the selected change, its existing delta spec,
   proposal, design, and tasks. Ground the update in the current contract and
   avoid duplicating unchanged canonical requirements in a delta.

5. **Write a valid OpenSpec requirement change**

   In a delta spec, group changes under `## ADDED Requirements`,
   `## MODIFIED Requirements`, and `## REMOVED Requirements`.

   - Use `### Requirement: <title>` followed by atomic, observable normative
     behavior using `SHALL`.
   - Give every requirement concrete, independently verifiable BDD scenarios
     with `#### Scenario: <title>` and optional `GIVEN`, required `WHEN`, and
     required `THEN` clauses.
   - For a modification, include the complete updated requirement and all of
     its scenarios. For a removal, include its heading and a concise rationale.
   - Add a dedicated scenario for each security-sensitive attack or misuse
     path.

6. **Reconcile the selected change**

   When updating an unarchived change, inspect `tasks.md` and `design.md` without
   waiting for further instruction.

   - When a completed change's requirement is corrected, reopen the change by
     unchecking every completed task whose code artifact is now incompatible,
     plus the verification and documentation tasks needed to safely reapply it.
   - Uncheck a completed task only when the code artifact it produced is now
     broken or incompatible; do not clear a task merely because its wording is
     stale.
   - Verify the relevant source before adding a new gap task. Add work only
     when the implementation does not already meet the updated requirement.
   - Update stale task descriptions while preserving completion when the code
     remains correct.
   - Record a design change only when a decision or context is contradicted;
     otherwise state that the design remains consistent.

   State which tasks were reset and that the change is reopened for
   `openspec-apply-change`; do not reject a completed but unarchived change as
   ineligible for a specification repair.

   If this update reveals partial implementation in the current turn, stop and
   ask whether to revert it or continue in apply mode. Switch to
   `openspec-apply-change` before making further implementation changes.

7. **Check downstream documentation and verification**

   Update `README.md` for user-visible behavior, commands, configuration, or
   features; update `docs/spec.md` for architecture, ownership, data-flow, or
   interface changes. State why neither changes when they are unaffected.

   Review tests for modified and removed requirements using the repository's
   hygienist workflow. Validate the result:

   ```bash
   openspec validate <capability> --type spec --strict
   ```

   For a delta, also validate its owning change strictly.

## Output

Report the capability and selected change, then list added, modified, and
removed requirements. Also state tasks cleared or added, design consistency,
documentation impact, test review, and validation results. End by saying
whether the delta is ready to synchronize at archive time.

## Guardrails

- Keep the canonical spec as the complete accepted contract and a delta spec as
  only the work-in-progress difference.
- Do not silently choose between reverting partial implementation and applying
  it; the user decides.
- Do not implement application changes while performing a spec-only update.
- Prefer the CLI's resolved paths and artifact status over inferred filesystem
  locations.
