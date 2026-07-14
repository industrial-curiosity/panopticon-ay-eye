## 1. Dependency index schema

- [ ] 1.1 Create `panopticon/dependencies.py` mirroring `panopticon/index.py`'s shape: `empty_index`,
      `validate_index`, `sorted_doc`, `dumps_index`, `save_index`, `load_index`, with `KIND_LOCAL` /
      `KIND_SHARD` / `KIND_COMPILED`, keyed on canonical dependency name instead of interface name.
- [ ] 1.2 Dependency-object validation: `ecosystem` (non-empty string, open vocabulary), `owner`
      (repo/component or `null`), `producer`/`consumer` repo-object lists, optional `links_to_interface`
      (`{"name": ..., "type": ...}`) on the object.
- [ ] 1.3 Repo-object validation: `repo`, `source_files` (as today), plus optional `apis` on consumer repo
      objects only — a deduplicated, sorted list of non-empty strings.
- [ ] 1.4 New conflict reason constant `unregistered-producer` alongside the existing
      `ownership-dispute`/`owner-attribution-mismatch` pair; validate the compiled-only `conflicts` array the
      same way `index.py` does.
- [ ] 1.5 Unit tests for schema validation covering: valid round-trip, empty-entry rejection, unknown-field
      rejection, `apis` allowed only on consumer objects, deterministic `dumps_index` ordering.

## 2. Org configuration

- [ ] 2.1 Add optional `internal_registries` field to `load_org_config` in `panopticon/config.py`: list of
      non-empty strings, default `[]`, validated the same way as `protected_paths`.
- [ ] 2.2 Unit tests: field present, field absent (defaults to `[]`), invalid entries rejected with the same
      error style as `protected_paths`.

## 3. Hint annotations

- [ ] 3.1 Extend `panopticon/naming.py` with `dependency_hints(text)` (parallel to `interface_hints`) for the
      `panopticon-dependency <name>` form, reusing `parse_hints`/`nearest_hint`.
- [ ] 3.2 Add `dependency_of_hints(text)` for the `panopticon-dependency-of <interface-name>` form, same
      scanning precedence (comment-adjacent for text formats, sibling-file precedence for comment-less JSON
      manifests, matching the existing interface-hint fallback for JSON).
- [ ] 3.3 Unit tests for both hint forms: pin a name, resolve a link, sibling-file precedence for JSON
      manifests, no-hint-present case.

## 4. Structural (zero-config) detection — Go

- [ ] 4.1 Create `panopticon/parsers/go_mod.py` implementing `detect(repo_root)` / `extract(repo_root)`
      following the existing parser-registry pattern (`kafka_topics.py`, `rest_openapi.py`).
- [ ] 4.2 Manifest-scan phase: parse `go.mod` `require` block, resolve the org identity from the instance
      repo's `instance` field, and mark modules under `github.com/{org}/...` as internal-dependency
      candidates with their declared version.
- [ ] 4.3 Self-registration phase: when the repo's own `go.mod` module path is under the org's identity,
      emit a producer candidate for that module — no further evidence required.
- [ ] 4.4 Source-scan phase (two-phase extraction): walk `.go` files' import blocks for import paths under a
      resolved internal module, aggregating distinct subpackage import paths into that consumer's `apis`.
- [ ] 4.5 Unit tests using fixture `go.mod`/`.go` files: consumer candidate with multiple subpackage imports,
      producer self-registration, non-internal (third-party) imports correctly excluded.

## 5. Registry-host detection and instance cross-reference

- [ ] 5.1 Add a shared `is_internal_registry(url_or_host, internal_registries)` helper (used by both
      consumer-side detection and producer-side self-registration per the design's "one field, two
      directions" decision).
- [ ] 5.2 Implement the no-checkout instance cross-reference: a single-file read of the instance repo's
      compiled dependency index via the GitHub API, authenticated with `PANOPTICON_INSTANCE_TOKEN` in CI.
- [ ] 5.3 Local-agent path: best-effort read via authenticated `gh`/local instance checkout when available;
      fall through to hint/LLM resolution without blocking when unavailable (mirrors the existing
      diagram-config no-checkout tolerance).
- [ ] 5.4 Tests: registry-host match/no-match, cross-reference hit, cross-reference unavailable falls through
      cleanly.

## 6. Extraction orchestration and LLM fallback

- [ ] 6.1 Add a dependency-extraction entry point alongside `panopticon/extraction.py`'s
      `extract_repo`/`llm_extract`, running the detection layers in order (structural → registry-host →
      instance cross-reference → hint → LLM) and applying `candidates_to_index`-equivalent assembly for the
      dependency schema.
- [ ] 6.2 LLM-extracted dependency candidates tagged `"extracted_by": "llm"`; extend
      `parser_gap_recommendations`/`write_step_summary` to cover dependency ecosystems/patterns with no
      parser, same as the existing interface-extraction gap reporting.
- [ ] 6.3 CI failure path: candidate unresolved by any layer fails the check with "add a
      `panopticon-dependency` hint" instructions.
- [ ] 6.4 Tests: LLM-fallback tagging, parser-gap recommendation text, CI-failure message content.

## 7. Shard merge, compiled index, and conflict detection

- [ ] 7.1 Add dependency equivalents of `merge.py`'s `compile_index`, `replace_shard`, `load_shards`,
      `merge_into_instance` for `dependencies/{repo}.json` → `dependencies/index.json`, independent of the
      existing interface merge path.
- [ ] 7.2 Conflict detection: reuse the `ownership-dispute` shape for two repos self-registering the same
      canonical dependency name; add the new `unregistered-producer` case (internal candidate, no
      self-registered producer), recomputed on every compiled-index rebuild.
- [ ] 7.3 Empty-entry removal: dependency object removed when both `consumer`/`producer` are empty; key
      removed when its object array is empty (mirrors `index.py`).
- [ ] 7.4 Tests: shard replace, compiled rebuild determinism (byte-identical for identical shards), both
      conflict reasons, empty-entry cleanup.

## 8. Diagram rendering

- [ ] 8.1 Extend `panopticon/diagrams.py`'s org-diagram generation to include dependency entries: same
      internal-only exclusion rule as interfaces, applied to dependency entries too.
- [ ] 8.2 Render dependency edges visually distinct from interface edges (e.g. dashed vs. solid) in the
      relationship diagram; combine a repo's interface and dependency relationships into one section/table
      per the modified `architecture-diagrams` spec.
- [ ] 8.3 Implement edge deduplication: when a dependency's `links_to_interface` matches an interface
      entry relating the same two repos, render one combined-label edge instead of two.
- [ ] 8.4 Tests: dependency-only repo gets a section, combined interface+dependency section, single-repo
      dependency excluded, linked-pair dedup, unlinked pair renders separately.

## 9. Documentation

- [ ] 9.1 Write the annotation reference documenting `panopticon-dependency` and `panopticon-dependency-of`
      (syntax, placement, effect) — extend the existing hint documentation if a suitable home exists, or
      create a new reference doc if not; close the gap already flagged in
      `docs/explore/interface-name-collisions.md` for interface hints in the same pass if in scope.
- [ ] 9.2 Update `docs/planned-work.md` to remove or check off the "Track internal dependencies" line.
- [ ] 9.3 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by
      this change.
