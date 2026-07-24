# Preserve the Instance Org Diagram During Template Sync

## Context

The template tracks an empty-state `docs/architecture.md` so new instances have
a working README link.
Instance merge tooling later regenerates that same path from the instance's
compiled interface and dependency
indices. Consequently, the template supplies the path initially, but the
instance becomes its authoritative
owner.

The sync workflow already configures `merge.ours.driver true`. It uses tracked
`.gitattributes` for protected
JSON configuration and regenerates `.git/info/attributes` for org-declared
`protected_paths`. The org diagram
fits neither category: it is generated state declared by the template itself.

## Goals / Non-Goals

## Goals

- Preserve an existing instance `docs/architecture.md` whenever a template merge
  needs to reconcile both
  sides' versions.
- Continue installing the template placeholder when the instance lacks the path.
- Work for common-history and unrelated-history syncs, including the workflow's
  `-X theirs` first-sync mode.
- Reuse the existing merge driver and untracked per-checkout attributes file.
- Keep the classification distinct from protected config and org customization.

## Non-Goals

- Protect arbitrary generated files or introduce a user-configurable
  generated-path list.
- Add `docs/architecture.md` to `PROTECTED_CONFIG_FILES` or
  `panopticon.config.json`.
- Change how the org diagram is rendered or regenerated.
- Change the first-sync strategy for ordinary template files.
- Add a second custom Git merge driver.

## Decisions

### Register a fixed generated path in `.git/info/attributes`

The pre-merge workflow step will always write `docs/architecture.md merge=ours`
alongside any dynamically
loaded `protected_paths`. The fixed path is declared directly by the workflow so
it is available before the
incoming template code has been merged and does not depend on instance
configuration.

Tracked `.gitattributes` was rejected because that file is itself part of the
histories being merged and
would blur this generated-state rule with protected JSON config.
`PROTECTED_CONFIG_FILES` was rejected because
the diagram is Markdown generated from indices, not instance configuration.
`protected_paths` was rejected
because preservation must not depend on every organization opting into or
maintaining a customization entry.

### Keep generated and customized paths separate in code and output

The inline Python step will define a fixed `generated_paths` tuple and
separately load `protected_paths` from
the org config. It will combine them only when writing `.git/info/attributes`,
deduplicating without changing
their ownership labels. The step summary will identify the fixed generated path
separately from the existing
org-declared customization section.

This makes the behavior auditable without implying that the org diagram is
hand-customized. It also prevents
an accidental future refactor from moving the path into the JSON config
registry.

### Reuse `merge.ours.driver true`

The workflow already registers the named driver before writing runtime
attributes. No new git configuration
is needed. A path that exists on both sides and requires reconciliation uses the
instance version. A path
absent from the instance is a normal incoming addition, so the template
placeholder is installed rather than
discarded.

### Test actual Git behavior across four repository shapes

`tests/test_sync_from_template.py` will retain real temporary repositories and
subprocess Git commands. The
helper will reproduce the workflow's fixed generated-path registration, then
cover:

1. Common history where both sides independently add `docs/architecture.md`.
2. Common history where both sides modify an existing file.
3. Unrelated histories where both sides contain different files and the merge
   uses `-X theirs`.
4. A template placeholder added when the instance has no file.

Mocks were rejected because the behavior under test is Git's attribute and
merge-driver semantics, including
the difference between add/add, modify/modify, and one-sided addition.

## Risks / Trade-offs

- **The workflow version that performs a sync comes from the instance's
  pre-merge HEAD** → Existing instances
  must install this workflow update once before relying on it to protect an
  already-diverged org diagram; new
  instances inherit it from the template.
- **A generated file manually edited in the instance also survives** → This is
  acceptable because the instance
  is authoritative for the path; the next deterministic diagram rebuild can
  replace manual edits.
- **An instance deletes the path while the template still has it** → A later
  template sync can restore the
  placeholder as a one-sided incoming path; deterministic generation remains the
  supported way to populate it.
- **Runtime attributes are invisible after the checkout is discarded** → The
  step summary labels the generated
  path, and integration tests lock down the fixed registration behavior.

## Migration Plan

1. Update the workflow's pre-merge attribute-registration step and comments.
2. Add the four real-git integration scenarios and retain the existing
   protected-path tests.
3. Update sync and testing documentation to describe the fixed generated path
   separately.
4. Install the updated workflow into existing instances before their next
   template merge if their org diagram
   already diverges from the template placeholder.
5. Roll back by removing the fixed generated-path registration; no tracked
   attributes or config migration is
   required.

## Open Questions

None. The path, merge driver, attribute location, ownership classification, and
required integration scenarios
are specified.
