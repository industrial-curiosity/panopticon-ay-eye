# 2026 07 14 Track Internal Dependencies Tasks

## 1. Dependency index schema

- [x] 1.1 Create `panopticon/dependencies.py` mirroring `panopticon/index.py`'s
  shape: `empty_index`,
      `validate_index`, `sorted_doc`, `dumps_index`, `save_index`, `load_index`,
      with `KIND_LOCAL` /
      `KIND_SHARD` / `KIND_COMPILED`, keyed on canonical dependency name instead
      of interface name.
- [x] 1.2 Dependency-object validation: `ecosystem` (non-empty string, open
  vocabulary), `owner`
      (repo/component or `null`), `producer`/`consumer` repo-object lists,
      optional `links_to_interface`
      (`{"name": ..., "type": ...}`) on the object.
- [x] 1.3 Repo-object validation: `repo`, `source_files` (as today), plus
  optional `apis` on consumer repo
      objects only — a deduplicated, sorted list of non-empty strings.
- [x] 1.4 New conflict reason constant `unregistered-producer` alongside
  `ownership-dispute` (the
      interface-indexing pair's second reason, `owner-attribution-mismatch`,
      doesn't apply here — a
      dependency has exactly one producer role, not per-repo attribution
      disagreement); validate the
      compiled-only `conflicts` array, with `claims` required non-empty only for
      `ownership-dispute`.
- [x] 1.5 Unit tests for schema validation covering: valid round-trip,
  empty-entry rejection, unknown-field
      rejection, `apis` allowed only on consumer objects, `links_to_interface`
      validation, both conflict
      reasons' `claims` requirements, deterministic `dumps_index` ordering
      (including `apis` dedup/sort).

## 2. Org configuration

- [x] 2.1 Add optional `internal_registries` field to `load_org_config` in
  `panopticon/config.py`: list of
      non-empty strings, default `[]`, validated the same way as
      `protected_paths`.
- [x] 2.2 Unit tests: field present, field absent (defaults to `[]`), invalid
  entries rejected with the same
      error style as `protected_paths`. Documented in `docs/setup-guide.md`'s
      org-config field list.

## 3. Hint annotations

- [x] 3.1 Extend `panopticon/naming.py` with `dependency_hints(text)` (parallel
  to `interface_hints`) for the
      `panopticon-dependency &lt;name&gt;` form, reusing `parse_hints`; generalized
      `nearest_hint` to accept a
      `hint_type` parameter (defaulting to `INTERFACE_HINT` so existing call
      sites are unaffected).
- [x] 3.2 Add `dependency_of_hints(text)` for the `panopticon-dependency-of
  <interface-name>` form, same
      comment-adjacent scanning precedence via `nearest_hint(...,
      hint_type=DEPENDENCY_OF_HINT)`.
      Sibling-file precedence for comment-less JSON manifests is deferred to
      whichever parser first needs it
      (no JSON-manifest dependency parser exists yet in this change — Go's
      `go.mod` supports `//` comments
      directly, so it never hits this case); tracked as a gap for the next
      contributed parser, not a
      regression here.
- [x] 3.3 Unit tests for both hint forms: pin a name, resolve a link,
  `nearest_hint` with each hint type,
      no-hint-present case. Sibling-file precedence test deferred alongside 3.2
      above.

## 4. Structural (zero-config) detection — Go

- [x] 4.1 Create `panopticon/parsers/go_mod.py` implementing `detect(repo_root)`
  / `extract(repo_root)`
      following the existing parser-registry pattern (`kafka_topics.py`,
      `rest_openapi.py`), with its own
      `DEPENDENCY_ECOSYSTEM` constant (not registered in the interface
      `REGISTRY` — a separate family, per
      `docs/parser-contribution.md`'s updated note).
- [x] 4.2 Manifest-scan phase: parse `go.mod`'s `require` block (and single-line
  form), resolve the org
      identity from the repo's own `panopticon/config.json` `instance` field (a
      local file, no network), and
      mark modules under `github.com/{org}/...` as internal-dependency
      candidates. The parsed version is used
      internally only to correctly identify `require` entries — it is not
      carried into the candidate or
      persisted anywhere, since version-drift tracking is an explicit design
      non-goal for this change.
- [x] 4.3 Self-registration phase: when the repo's own `go.mod` module path is
  under the org's identity,
      emit a producer candidate for that module — no further evidence required.
- [x] 4.4 Source-scan phase (two-phase extraction): walk `.go` files' import
  blocks for import paths under a
      resolved internal module, aggregating distinct subpackage import paths
      into that consumer's `apis`
      (one candidate per importing file; folding/union across files happens in
      the extraction-orchestration
      layer, group 6). `panopticon-dependency`/`panopticon-dependency-of` hints
      are resolved per require line
      via the generalized `nearest_hint`, matching the precedent set by
      `rest_openapi.py`/`kafka_topics.py`
      resolving interface hints inside the parser itself.
- [x] 4.5 Unit tests (`tests/test_dependency_parsers.py`, fixture
  `sample_go_repo/`): consumer candidate with
      multiple subpackage imports, producer self-registration from module path
      alone, non-internal
      (third-party) require producing no candidate, `panopticon-dependency-of`
      hint resolution, and a repo
      with no `panopticon/config.json` yielding no candidates rather than
      guessing the org identity.

## 5. Registry-host detection and instance cross-reference

**Design correction found during implementation** (see `design.md`'s decision 3
and the corresponding spec
requirement, both updated): CI does not need a live API read at all —
`panopticon-pr.yml`/`panopticon-merge.yml`
already run a full `actions/checkout` of the instance repo before any check
runs, so the CI-side
cross-reference is a plain filesystem read, matching how every other CI-side
instance-repo read in this
codebase already works. The live-API fallback is needed only for the
local-agent, no-checkout case.

- [x] 5.1 Add a shared `is_internal_registry(url_or_host, internal_registries)`
  helper (used by both
      consumer-side detection and producer-side self-registration per the
      design's "one field, two
      directions" decision).
- [x] 5.2 Implement the instance cross-reference as a plain read of
  `dependencies/index.json` from an
      instance-repo root path (checkout already present in CI — no API call, no
      new auth mechanism).
- [x] 5.3 Local-agent path: best-effort live GitHub API read (mirroring
  `org_diagram_link.py`'s
      `_resolve_token`/`_fetch_default_branch`: `GH_TOKEN`/`GITHUB_TOKEN`/`gh
      auth token`, single GET, `None`
      on any failure) when no local instance checkout is available; fall through
      to hint/LLM resolution
      without blocking either way (mirrors the existing diagram-config
      no-checkout tolerance).
- [x] 5.4 Tests: registry-host match/no-match (including scheme/path-bearing
  URLs, not just bare hosts),
      cross-reference hit from a checkout, cross-reference hit via the live-API
      path (stubbed `urlopen`),
      cross-reference unavailable (no checkout, no token, `gh` absent) falls
      through cleanly.

## 6. Extraction orchestration and LLM fallback

- [x] 6.1 Add `panopticon/dependency_extraction.py`, mirroring
  `panopticon/extraction.py`'s
      `extract_repo`/`llm_extract`/`candidates_to_index` shape for the
      dependency schema
      (`dependency_candidates_to_index`, `detecting_dependency_parsers`,
      `run_dependency_parsers`).
      `resolve_dependency_name` (naming.py) is used instead of `resolve_name` —
      deliberately no
      lowercase/dash normalization, since a dependency's raw name is already a
      canonical machine
      identifier (see that function's docstring). Layers 2–3 (registry-host,
      instance cross-reference)
      are implemented as the standalone, independently-tested
      `resolve_candidate_internality` — no
      shipped parser produces candidates that need them yet, since `go_mod`
      fully self-resolves
      (layer 1); wiring a future non-self-resolving parser's candidates through
      it is the remaining
      integration point, not new logic. `panopticon-dependency-of` hints resolve
      into a full
      `links_to_interface: {name, type}` by checking the repo's own local
      interface index; left unset
      (not fabricated) when the named interface isn't found there or no
      `repo_root` is given.
      **Scope addition found necessary during implementation**:
      `panopticon/dependencies.py` was
      missing from `LOCAL_TOOLING_MODULES` (`bootstrap.py`/`sync.py`) and
      `panopticon/__init__.py`'s
      module list — without it, no child repo could vendor the schema module
      needed to save/validate
      a local dependency index at all. Fixed in all three places.
- [x] 6.2 LLM-extracted dependency candidates tagged `"extracted_by": "llm"` via
      `panopticon/dependency_extraction.py`'s `llm_extract`, guided by the new
      `.agents/skills/panopticon-dependency-extraction/SKILL.md` (mirroring
      `panopticon-interface-extraction`'s response contract, adapted for
      `ecosystem`/`apis`/
      `links_to_interface_hint`).
      `parser_gap_recommendations`/`write_step_summary` extended for
      dependency ecosystems with no parser, same shape as the existing
      interface-extraction gap
      reporting. Also added
      `.agents/skills/panopticon-dependency-naming/SKILL.md` (mirroring
      `panopticon-interface-naming`) to guide the local agent's internality/hint
      judgment — closes the
      gap explicitly deferred in task 3's hygiene pass, now that the full flow
      exists end-to-end.
- [x] 6.3 CI failure path: `resolve_dependency_name` raises
  `UnresolvableNameError` naming
      `panopticon-dependency` (not the interface hint) when no layer resolves a
      candidate, matching
      the interface-indexing capability's "CI cannot resolve a name" behavior.
- [x] 6.4 Tests (`tests/test_dependency_extraction.py`, 21 cases):
  parser-registry grouping, a full
      `extract_repo` pass over `sample_go_repo/` with unioned
      `source_files`/`apis` across multiple
      candidates for the same dependency, unresolvable-name failure message,
      `links_to_interface`
      resolution (found, not-found-locally, no-`repo_root`),
      `resolve_candidate_internality` via both
      registry-host and instance cross-reference, fallback-file selection, and
      the full `llm_extract`
      contract (tagging, gap reporting, skill loading,
      malformed/prose/code-fenced responses, retry
      recovery) reusing the shared `FakeClient` from `test_extraction.py`.

## 7. Shard merge, compiled index, and conflict detection

- [x] 7.1 Add `panopticon/dependency_merge.py` with dependency equivalents of
  `merge.py`'s
      `compile_index`, `shards_from_compiled`, `replace_shard`, `load_shards`,
      `merge_into_instance`,
      `simulate_merge`, `diff_compiled`, `format_report`, `collect_actions`, and
      CLI `main`, for
      `dependencies/{repo}.json` → `dependencies/index.json`, entirely
      independent of the existing
      interface merge path/files. **Deliberately does not rebuild the org
      diagram** (unlike
      `merge.merge_into_instance`) — `panopticon.diagrams` doesn't render
      dependency edges until group
      8 lands; wiring both merge paths to one shared, dependency-aware diagram
      writer is group 8's job
      (see this file's module docstring and `design.md`'s Non-Goals for the
      related, separately-flagged
      CI-workflow-wiring gap).
- [x] 7.2 Conflict detection: reuse the `ownership-dispute` shape (self-claims
  only — see the module
      docstring for why a dependency has no `owner-attribution-mismatch`
      equivalent: nothing in the
      extraction path ever sets a shard's owner to a repo other than itself) for
      two repos
      self-registering the same canonical name; `unregistered-producer` fires
      when a compiled entry's
      folded `producer` list is empty (mechanical — no extra provenance tracking
      needed, since an entry
      only exists at all when it has a consumer or producer, so an empty
      producer list already implies
      a consumer-only entry), recomputed on every compiled-index rebuild.
- [x] 7.3 Empty-entry removal: dependency object removed when both
  `consumer`/`producer` are empty; key
      removed when its object array is empty (mirrors `index.py`, verified via
      `TestEntryLifecycle`).
- [x] 7.4 Tests (`tests/test_dependency_merge.py`, mirroring `test_merge.py`):
  shard replace, compiled
      rebuild determinism and round-trip fidelity, both conflict reasons
      (including that a non-self
      owner claim is silently ignored rather than fabricating a third conflict
      category), empty-entry
      cleanup, simulation/merge parity, the CLI's exit-code contract. (The
      org-diagram-writing tests
      were updated in group 8 once `diagrams.py` learned to render dependencies
      — see 8.4.)

## 8. Diagram rendering

- [x] 8.1 Extended `panopticon/diagrams.py`: `repo_set`/`_other_repo_role` are
  reused unchanged for
      dependency entries (identical owner/producer/consumer shape); a new
      `_rows_for_index` helper
      builds rows from either compiled index, tagged with `kind`;
      `relationships_for_repo` gained an
      optional `dependencies_compiled` parameter (defaults to empty — existing
      interface-only callers
      unaffected) and combines rows from both. Same internal-only exclusion rule
      applies to
      dependencies automatically, since it's driven by `repo_set` alone.
- [x] 8.2 `_mermaid_graph` picks an arrow style by `row["kind"]` (`-.->`
  interface, `-->` dependency,
      `==>` linked — corrected in a later pass, see the spec's "Org diagram
      document shape"); `_table`
      gained a `Kind` column. `render_org_diagram` gained an optional
      `dependencies_compiled`
      parameter and now collects repos from both indices, rendering one combined
      section per repo
      covering both kinds.
- [x] 8.3 `_dedupe_linked_rows`: when a dependency row's `links_to_interface`
  names an interface row
      relating the same two repos, collapse them into one `kind: "linked"` row
      (combined name label,
      thick/double edge) — matching only on an explicit hint-derived link, never
      inferred.
      **Also resolved during this group**: wired
      `dependency_merge.merge_into_instance` to call the
      same `diagrams.write_org_diagram` as `merge.merge_into_instance`
      (previously deliberately
      deferred in group 7, since `diagrams.py` didn't support dependencies yet).
      `write_org_diagram`'s
      signature changed from accepting an in-memory compiled doc to reading both
      compiled indices
      fresh from `instance_root` on disk, so either merge path always renders
      the other index's
      current state too — resolving the "which merge rebuilds the diagram" open
      thread from the
      original exploration and from `design.md`'s Non-Goals.
- [x] 8.4 Tests: `tests/test_diagrams.py`'s new
  `TestCombinedInterfaceAndDependencyRendering` class
      (dependency-only section, combined section not duplicated, single-repo
      dependency excluded,
      solid-vs-dashed edge styling, linked-pair dedup with thick edge, unlinked
      pair renders
      separately); `tests/test_dependency_merge.py` updated to confirm the org
      diagram is now written
      with dependency edges and still reflects the instance's current interface
      state.

## 9. Documentation

- [x] 9.1 Created `docs/hint-reference.md`: syntax, placement, and effect for
  every hint form that
      actually exists in the tooling (`panopticon-interface`,
      `panopticon-dependency`,
      `panopticon-dependency-of`), including the
      CI-fails-loudly-with-an-instruction contract.
      Verified `panopticon-component` (seen in a `test_naming.py` fixture) is
      not a real, consumed
      hint type anywhere in the codebase — not documented as one. Cross-linked
      from
      `docs/setup-guide.md` and both naming skills. **Scoped narrower than the
      task's "if in
      scope" offer**: did not attempt to close
      `docs/explore/interface-name-collisions.md`'s
      broader getting-started-guide gap (conflict category explanations, worked
      examples, a full
      TOC) — that's a separate, larger, still-unproposed exploration thread;
      expanding into it here
      would be a significant unplanned scope increase beyond what this change's
      proposal/spec
      committed to.
- [x] 9.2 Removed the "Track internal dependencies" line from
  `docs/planned-work.md` (this change
      delivers it).
- [x] 9.3 Updated README.md: overview and repository-role bullets now mention
  dependency-indexing;
      new "The dependency index" section mirroring "The interface index";
      Lifecycle section gained
      an explicit, honest status note that CI workflow wiring isn't done yet
      (see design.md's
      Non-Goals) while local/manual use of the tooling is fully supported;
      Repository layout lists
      every new module, directory, config field, and skill. No `docs/spec.md`
      exists in this repo
      (an apply-skill template convention, not an actual file here) — README.md
      and
      `docs/setup-guide.md` are this repo's equivalent architecture/setup
      references, both updated.
