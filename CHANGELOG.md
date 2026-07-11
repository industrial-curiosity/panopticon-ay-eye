# Changelog

All notable changes to Panopticon are documented in this file.

## [0.1.0] - 2026-07-10

First usable release: an org-wide interface catalog and documentation system, initialized from a
GitHub template, with LLM-assisted extraction/naming, deterministic conflict detection, and CI
gating for pull requests. Established across `openspec/changes/establish-panopticon-core`.

### Added

**Interface indexing** (`interface-indexing`)
- JSON index schema (`schema_version`, name-keyed interface objects with `owner`, `type`,
  `consumer`/`producer` repo lists), describing code state — not deployment state — on a branch.
- Deterministic parser registry (`detect`/`extract` contract), with starter parsers for
  REST/OpenAPI and Kafka topic configs.
- LLM extraction fallback for interface types with no deterministic parser, tagged
  `extracted_by: "llm"`, with parser-gap recommendations surfaced in the CI summary.
- Name normalization and matching: deterministic rules plus local LLM judgment, persisted as
  `panopticon-interface` hint comments; CI resolves names from hints and rules alone, with no LLM
  judgment calls during compile.
- Shard replace + deterministic compiled-index rebuild, and conflict detection
  (`ownership-dispute`, `owner-attribution-mismatch`) recomputed on every rebuild.

**Agent runtime** (`agent-runtime`)
- Provider-agnostic, stdlib-only LLM client for CI (litellm-compatible `/chat/completions`), with
  retries and fail-loud behavior on missing configuration or unreachable endpoints.
- Skill-based prompting: the same markdown skill files drive both CI and local agent-harness
  execution, so behavior is versioned once and shared between the two.

**Documentation generation** (`doc-generation`)
- Four generated documentation layers per repo (architecture overview, per-component docs,
  interface docs, operational docs), regenerated in place with no stale sections left behind.
- Interface docs are deterministically rendered from the local index — never hand-edited or
  LLM-authored — so they can never disagree with it.
- LLM-based doc-drift check for CI, with self-contained, actionable remediation instructions
  (exact command/skill per stale doc) in the GitHub Actions summary and PR comment.
- Initialization-time drift resolution: local agent runs revise documentation that contradicts the
  current repo state, recording what was resolved in `panopticon-changelog.md` rather than
  cluttering the docs themselves; genuinely ambiguous cases prompt the user instead of guessing.

**Repo initialization** (`repo-initialization`)
- Stdlib-only bootstrap installer (`install.py`), runnable via `curl | python3` with no local
  instance clone, including piped-execution self-bootstrapping and a GitHub API retry/backoff
  contract for transient failures.
- Interactive skills-location selection (arrow-key menu with typed fallback, environment-variable
  override, idempotent re-run reuse) across every supported agent-harness tool.
- `panopticon-init` orchestrating skill sequencing interface naming, extraction, doc generation,
  and finalization in dependency order, with a resumable checkpoint log.
- Three-phase initialization (deterministic bootstrap → AI-driven agent pass → deterministic
  finalization), writing `panopticon/config.json` only after validation passes.
- Default-branch workflow-ref resolution requiring no manual tagging step on a fresh instance,
  with org-configurable pinning.

**PR evaluation** (`pr-evaluation`)
- Reusable PR workflow: initialization check, doc-drift check, index-currency check, pre-merge
  index simulation (dry-run over the same merge code path as the real merge), and
  `{repo}/{branch}` branch-state push to the instance repo.
- Org-configurable gating per check type (init/doc-drift blocking, interface-conflict advisory, by
  default), read from the instance repo's `panopticon.config.json` rather than hardcoded.
- Combined report: a de-duplicated TL;DR leading (and trailing) the GitHub Actions summary and PR
  comment, collapsing every doc-drift/index-currency finding into a single "run
  panopticon-doc-generation once" action regardless of how many docs or the index are affected.
- CI checks distinguish an operational failure (crash, malformed LLM response, unreachable
  endpoint) from a genuine business verdict by a fixed exit-code contract, so a check that could
  not run is never silently misreported as passing or as a stale-docs finding — and every
  independent check still runs and reports its own outcome regardless of an earlier failure.

**Master sync** (`master-sync`)
- Merge-to-main sync workflow: docs copied to `docs/{repo}/`, index shard replaced wholesale,
  compiled index rebuilt, pushed directly to the instance repo's default branch (no PR).
- Fetch-rebase-retry loop for concurrent pushes from multiple child repos, touching only the
  compiled-index rebuild on retry — shards are never cross-modified.
- Conflict-issue creation in both the instance and child repo on a merge conflict, cross-linked,
  updating the existing issue rather than opening duplicates across repeated merges.
- Instance branch lifecycle: the matching `{repo}/{branch}` branch is deleted when a PR closes.

### Fixed

- Module-shadowing bug where the child repo's vendored `panopticon/` subset silently shadowed the
  instance repo's full package during CI checks (`python -m`/`-c` prepend cwd to `sys.path` ahead
  of `PYTHONPATH`), fixed via `PYTHONSAFEPATH=1` at job level.
- Exit-code collision where an uncaught check exception and a genuine "stale" verdict produced the
  same exit code, causing crashes to be silently misreported as business verdicts.

[0.1.0]: https://github.com/industrial-curiosity/panopticon-ay-eye/releases/tag/v0.1.0
