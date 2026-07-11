## 1. Spike: protected-config merge mechanism (blocks group 7)

- [x] 1.1 In a sandbox instance repo, verify whether a `.gitattributes` `merge=ours` custom driver engages
      during `sync-from-template.yml`'s first-sync path (`--allow-unrelated-histories -X theirs`, no common
      ancestor) as well as its routine-sync path (default merge strategy)
- [x] 1.2 Record the outcome in `design.md`'s Open Questions, resolving whether group 7 uses the
      `.gitattributes` driver approach or the documented fallback (explicit post-merge restore step)

## 2. Diagram configuration and format registry

- [x] 2.1 Define `panopticon.diagram.config.json` schema (`{"format": "mermaid"}`) and its default in
      `panopticon/config.py` (or a new sibling module)
- [x] 2.2 Add a `load_diagram_config()` (or equivalent) that reads the instance repo's config with the
      `mermaid` default applied when the file is absent
- [x] 2.3 Add the protected-config registry (`{path: template-default}`), starting with
      `panopticon.diagram.config.json`, in the same module
- [x] 2.4 Add a format-support check that fails loudly ("unknown diagram format") for any configured format
      with no implemented renderer, rather than silently no-op-ing

## 3. Per-repo diagram generation

- [x] 3.1 Add a `## Architecture diagram` section (one fenced code block in the configured format) to
      `architecture-template.md`
- [x] 3.2 Update the `panopticon-doc-generation` skill: rules for drawing the per-repo component/data-flow
      diagram grounded in the actual code, and for writing the back-link to the org diagram's anchor for this
      repo (derived from `panopticon/config.json`'s `instance` field)
- [x] 3.3 Extend `panopticon.docs.validate_docs()` (or add a sibling function) to check the section and fenced
      block exist and are well-formed, reusable by both local validation and the new PR check in group 4

## 4. Diagram-existence PR check

- [x] 4.1 Add `diagram-missing` to `panopticon/config.py`'s `CHECK_TYPES` and `DEFAULT_GATING` (default
      `advisory`, per the migration plan)
- [x] 4.2 Add a deterministic check step to `panopticon-pr.yml` (after the instance-repo checkout step) that
      calls the group-3.3 validation and reports pass/fail with no LLM call (implemented as a new
      `panopticon/diagram_check.py` module, mirroring drift.py/currency.py's exit-code/report/actions-file
      shape, called from a new "Diagram-existence check" step)
- [x] 4.3 Wire the check's outcome into the combined report (TL;DR collapses with doc-drift/index-currency,
      per the modified pr-evaluation spec) and into the gating step

## 5. Doc-drift scope extension

- [x] 5.1 Update the `panopticon-doc-drift` skill prompt to explicitly judge the diagram section's staleness
      alongside prose, using the same stale-doc reason format
- [x] 5.2 Confirm the combined-report TL;DR collapsing logic treats a stale-diagram finding the same as any
      other stale-doc finding (single collapsed action, no separate line) — no code change needed:
      `drift.py`'s `collect_actions()` already emits the same `run_doc_generation` action for any stale
      verdict regardless of which doc(s) triggered it, so a diagram-staleness reason collapses identically
      to a prose-staleness one; covered by group 8.2's tests

## 6. Org diagram rebuild

- [x] 6.1 Create `panopticon/diagrams.py` with a pure rendering function: compiled index in, org diagram
      markdown out — per-repo alphabetical sections, relationship diagram + interface table, internal-only
      exclusion rule (`len(repo_set) > 1`)
- [x] 6.2 Wire the renderer into `merge_into_instance()` (`panopticon/merge.py`), called right after
      `compile_index(shards)`, writing to `docs/architecture.md` at the instance repo root
- [x] 6.3 Confirm the existing `panopticon-merge.yml` commit step picks up the new file with no additional
      workflow changes (same commit as the compiled index rebuild) — verified: the step does `git add -A`
      over the whole instance-root checkout after calling `panopticon.merge merge`, so `docs/architecture.md`
      is staged and committed identically to `interfaces/index.json`, no workflow YAML change needed

## 7. Protected-config sync (depends on group 1's spike outcome)

- [x] 7.1 Implement path protection in `sync-from-template.yml` for every path in the group-2.3 registry,
      using whichever mechanism the group-1 spike validated (`.gitattributes` `merge=ours` +
      `git config merge.ours.driver true` registered as a workflow step before merging)
- [x] 7.2 Implement the field-diff warning step: compare top-level JSON keys between the incoming template
      version and the instance's current file for each registered path, emitting a non-blocking
      `::warning::` naming the file and the differing fields
- [x] 7.3 Verify a full sync run (both first-sync and routine-sync paths) leaves a customized
      `panopticon.diagram.config.json` untouched and produces the expected warning when the template's
      shipped default gains or loses a field — verified end-to-end against the real `.gitattributes`,
      `panopticon/config.py`, and the workflow's field-diff Python snippet in sandbox template/instance
      repos (not just the group-1 abstract spike): first-sync (`-X theirs`,
      `--allow-unrelated-histories`) and routine-sync (common ancestor) both preserved the instance's
      customized format, and the field-diff step correctly warned when a simulated future template
      version shipped a new `renderer_version` field

## 8. Tests

- [x] 8.1 Unit tests for the diagram-config default/override/unknown-format behavior (group 2)
      (`tests/test_config.py::TestDiagramConfig`)
- [x] 8.2 Unit tests for `validate_docs()`'s diagram-section check, including malformed cases (missing
      section, missing fenced block, wrong-language fenced block) (`tests/test_docs.py::TestDiagramSection`);
      plus `tests/test_diagram_check.py` for the new CI-facing `diagram_check.py` module's report
      formatting, `collect_actions`, and `main()`'s exit-code contract (not separately enumerated in this
      task list, but part of group 4's scope and following the same test pattern as drift.py/currency.py)
- [x] 8.3 Unit tests for `panopticon/diagrams.py`'s org-diagram rendering, including the internal-only
      exclusion rule and alphabetical section ordering (`tests/test_diagrams.py`)
- [x] 8.4 Integration test for `merge_into_instance()` producing the org diagram alongside the compiled index
      (`tests/test_merge.py::TestOrgDiagramRebuild`)

## 9. Documentation

- [x] 9.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by
      this change — this repo has no `docs/spec.md`; README.md is the architecture doc and was updated
      (lifecycle steps, repository layout, instance-repo description). `docs/setup-guide.md` (org-owner
      setup instructions) and `docs/testing.md` (test suite layout) were also updated since they're
      user-facing docs directly affected by this change (new gating config field, new checks, new test
      modules)
