---
name: openspec-update-change
description: Update an OpenSpec requirement or scenario. Use when the user asks to add, modify, remove, refine, or repair a specification; update an active change's delta spec; or resolve a canonical-spec issue that blocks validation or archive synchronization.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.4.1"
---

Update OpenSpec artifacts while keeping canonical specifications, active change
deltas, implementation tasks, and design decisions aligned.

## Steps

1. **Identify the capability and requested change**

   Use a named capability when supplied. Otherwise, infer it from the
   conversation or inspect `openspec/specs/` and ask the user only if the
   target remains ambiguous. State the selected capability and whether the
   work adds, modifies, or removes requirements.

2. **Resolve the correct planning context**

   Run:

   ```bash
   openspec list --json
   ```

   Use the relevant active change when one clearly owns the work. If several
   active changes could apply, ask the user which to update. Resolve paths from
   `openspec status --change "<change-name>" --json`; do not assume a
   repository-local change path when the CLI provides planning-home paths.

   Write a delta spec for an active change. Update a canonical spec directly
   only when there is no related active change or the user explicitly asks to
   repair the canonical specification.

3. **Read before writing**

   Read the canonical spec and, for an active change, its existing delta spec,
   proposal, design, and tasks. Ground the update in the current contract and
   avoid duplicating unchanged canonical requirements in a delta.

4. **Write a valid OpenSpec requirement change**

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

   For a canonical spec, retain one H1, a non-empty `## Purpose`, and a single
   `## Requirements` section containing every requirement. Integrate additions
   and modifications in place, remove retired requirements, and ensure the
   first physical line of each requirement's normative text contains `SHALL` or
   `MUST` so strict validation recognizes it.

5. **Reconcile the active change**

   When updating an active change, inspect `tasks.md` and `design.md` without
   waiting for further instruction.

   - Uncheck a completed task only when the code artifact it produced is now
     broken or incompatible; do not clear a task merely because its wording is
     stale.
   - Verify the relevant source before adding a new gap task. Add work only
     when the implementation does not already meet the updated requirement.
   - Update stale task descriptions while preserving completion when the code
     remains correct.
   - Record a design change only when a decision or context is contradicted;
     otherwise state that the design remains consistent.

   If this update reveals partial implementation in the current turn, stop and
   ask whether to revert it or continue in apply mode. Switch to
   `openspec-apply-change` before making further implementation changes.

6. **Check downstream documentation and verification**

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

Report the capability and target (canonical spec or active change), then list
added, modified, and removed requirements. For active changes, also state
tasks cleared or added, design consistency, documentation impact, test review,
and validation results. End by saying whether the delta is ready to synchronize
at archive time or the canonical spec was updated directly.

## Guardrails

- Keep the canonical spec as the complete accepted contract and a delta spec as
  only the work-in-progress difference.
- Do not silently choose between reverting partial implementation and applying
  it; the user decides.
- Do not implement application changes while performing a spec-only update.
- Prefer the CLI's resolved paths and artifact status over inferred filesystem
  locations.
