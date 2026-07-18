# Changelog

All notable changes to Panopticon are documented in this file.

## [0.1.5] - 2026-07-18

The public installer now dispatches securely to instance-owned installers for both public and private
repositories, and template sync preserves the instance-generated organization diagram. Established
across `add-template-installer-wrapper` and `fix-org-diagram-template-sync`.

### Changed

**Repo initialization** (`repo-initialization`)
- A single public template launcher now supports public and private instance repositories. It resolves
  the instance, ref, and authentication before handing control to the instance-owned installer, allowing
  customized installers to retain their own prompts, parameters, and behavior.
- The launcher accepts GitHub Contents API line-wrapped base64 while retaining strict base64 and UTF-8
  validation, and keeps prompted or configured tokens out of URLs, command arguments, output, errors,
  and persistent storage.

**Architecture diagrams** (`architecture-diagrams`)
- Template sync now classifies `docs/architecture.md` as a fixed, template-declared but instance-owned
  generated path. Existing instance diagrams win merges, while the template placeholder is installed
  when an instance does not yet have the file.

### Fixed

- Routine and first-time template sync no longer conflict on or overwrite an instance's generated
  `docs/architecture.md`; the workflow registers `merge=ours` in `.git/info/attributes` before merging
  without misclassifying the path as protected JSON configuration or org customization.
- The public installer no longer rejects valid GitHub Contents API payloads solely because their base64
  content contains transport line wrapping.

## [0.1.4] - 2026-07-15

`panopticon-init` now wires dependency indexing into the standard initialization flow, so every
newly initialized repo gets a populated dependency index alongside its interface index instead of
requiring dependency indexing as a separate, easy-to-forget manual step. Established across
`openspec/changes/init-dependency-steps`.

### Added

**Repo initialization** (`repo-initialization`)
- `panopticon-init`'s orchestration grows from four steps to six: `panopticon-dependency-naming`
  and `panopticon-dependency-extraction` now run between interface extraction and doc generation,
  so a `panopticon-dependency-of` hint can reference an already-built interface index and
  generated docs include dependency edges from the first `/panopticon-init` run.
- The checkpoint log (`panopticon/.init-log.json`) tracks the two new steps, preserving resumable
  init across an interrupted agent session.

### Notes

- End-to-end verification of a full `/panopticon-init` run against a real repo with genuine
  internal dependencies is deferred to the next real initialization — no fixture child+instance
  repo pair with a real cross-repo dependency exists in this workspace, and the orchestration is
  agent-followed skill instructions with no Python test harness to simulate it.

## [0.1.3] - 2026-07-15

Discoverable architecture-diagram links at the top of every instance and child repo README, and a
non-dead placeholder org diagram for a freshly created instance. Established across
`openspec/changes/readme-architecture-links`.

### Added

**Architecture diagrams** (`architecture-diagrams`)
- Child repo `README.md` now links to both diagrams at the top, own-repo above org: a relative link to
  this repo's own `architecture.md`, and a fully-qualified GitHub URL to the org diagram — obtained by
  running `python3 -m panopticon.org_diagram_link` and using its printed output verbatim, so the two can
  never disagree — written by `panopticon-doc-generation` as part of its normal architecture-overview
  pass.
- Instance repo `README.md` now links to the org diagram at the top (`docs/architecture.md`) only — no
  per-child-repo links, since the org diagram itself already enumerates every repo.
- `write_org_diagram` renders an explicit empty-state placeholder — a link to initializing a child repo
  plus a hexagon of six `?` nodes — in place of a bare "no relationships yet" line, produced by the same
  deterministic render path every run rather than written once and left stale.
- The template repo ships that placeholder `docs/architecture.md` directly, so a freshly created
  instance repo's architecture link is never dead even before any child repo has merged; its own
  `README.md` Overview section now carries org-agnostic instance-appropriate text plus a maintainer note,
  replacing template self-description that no longer applies once copied into an instance repo via "Use
  this template."

## [0.1.2] - 2026-07-14

Internal (same-org) library/package dependency tracking, as a relationship distinct from runtime
interfaces, with its own schema, parsers, merge/conflict detection, and combined org-diagram
rendering. Established across `openspec/changes/track-internal-dependencies`.

### Added

**Dependency indexing** (`dependency-indexing`, new capability)
- Separate JSON index schema (`dependencies/{repo}.json` shards, `dependencies/index.json`
  compiled) — own files, never recorded as an interface `type` — with `owner`/`producer`/`consumer`
  and, on consumer repo objects, `apis`: a deduplicated, sorted list of the specific modules the
  consumer imports (import-level granularity, not call-site).
- Layered internality detection, most portable first: zero-configuration structural resolution for
  ecosystems whose declarations embed the org's own GitHub identity (Go module paths under
  `github.com/{org}/...`, the first deterministic parser); an org-declared `internal_registries`
  config field, reused for both consumer-side detection and producer self-registration; a
  no-checkout instance cross-reference (a plain filesystem read in CI, since the shared workflows
  already check out the instance repo; a best-effort live GitHub API read locally); and a
  `panopticon-dependency` hint / LLM fallback for anything else, with the same parser-gap
  reporting contract as interfaces.
- `panopticon-dependency-of <interface-name>` hint: links a dependency that's really a
  packaged/generated client for an interface this org already tracks — never inferred from naming
  conventions, only set explicitly.
- Shard replace, deterministic compiled-index rebuild, and conflict detection
  (`ownership-dispute`, and the dependency-specific `unregistered-producer`: an internal candidate
  with consumers but no self-registered producer anywhere).
- `docs/hint-reference.md`: syntax, placement, and effect for every hint form in the tooling
  (`panopticon-interface`, `panopticon-dependency`, `panopticon-dependency-of`).

**Architecture diagrams** (`architecture-diagrams`)
- The org diagram now renders dependency edges alongside interface edges in one combined section
  per repo — dashed for interfaces, solid for dependencies — and collapses a dependency linked to
  an interface via `panopticon-dependency-of` into a single edge instead of two.

### Notes

- CI workflow wiring (the shared `panopticon-pr.yml`/`panopticon-merge.yml` invoking the new
  extraction/merge tooling automatically) is not yet included — local/manual use of
  `python3 -m panopticon.dependency_extraction` / `dependency_merge` is fully supported today,
  matching the existing precedent that full-repo interface extraction is also local-only.

## [0.1.1] - 2026-07-12

Tooling-currency detection for child repos, plus robustness fixes surfaced by exercising the
0.1.0 release end-to-end. Established across `openspec/changes/tooling-currency` and
`openspec/changes/robust-llm-verdicts`.

### Added

**Tooling currency** (`tooling-currency`, new capability)
- Advisory-only PR check warning when a child repo's wired workflow ref, downloaded skills, or
  vendored local tooling have drifted from the instance repo's current default branch —
  content-based comparison only, never timestamps, and never gated or folded into the combined
  TL;DR report.
- `python3 -m panopticon.sync`: pulls the instance's current skills and tooling into an
  already-bootstrapped child repo on demand, overwriting unconditionally (git review is the
  safety net); `--check-updates` reports what would change via a git-blob-hash comparison without
  writing anything.
- Org-declared `protected_paths` in `panopticon.config.json`: arbitrary instance-level
  customizations (skills, tooling modules) excluded from `sync-from-template`'s merge via
  `.git/info/attributes` (never a commit, never the tracked `.gitattributes`), printed to the sync
  run's step summary since the protection itself is invisible in the tracked tree.

**Repo initialization** (`repo-initialization`)
- `PANOPTICON.md`: a concise, static getting-started guide downloaded to every child repo's root
  on bootstrap, covering the three repo roles, where architecture diagrams live, and how to run
  the sync script; the bootstrap script's printed output now names both on every run.
- `panopticon/config.json` gains `instance_default_branch`, resolved via the same GitHub
  token/transport mechanism the bootstrap script already uses for every other request (never a
  `gh api` subprocess call, which depends on `gh auth login` specifically) — refreshed in place on
  every bootstrap rerun of an already-initialized repo.
- Bootstrap now writes `panopticon/.gitignore` (`__pycache__/`) alongside the vendored local-tooling
  modules, so running them (as the bundled skills instruct) never leaves compiled bytecode staged
  on the next `git add -A`.

**Architecture diagrams** (`architecture-diagrams`)
- `python3 -m panopticon.org_diagram_link`: prints an immediately clickable link to a child repo's
  section of the org-wide diagram, for use before that repo's docs have been merged into the
  instance (the embedded in-doc link only resolves after merge). Reads local config first with no
  network call; falls back to a live lookup only when needed.

**Agent runtime** (`agent-runtime`)
- Structured LLM responses (doc-drift, index-currency, interface-extraction verdicts) now recover
  from a non-compliant first response via one shared, bounded corrective-retry method instead of
  failing outright — the model's non-compliant answer plus a specific correction are appended to
  the conversation and retried before failing loudly. No provider-specific request parameters, so
  this works across any litellm-compatible endpoint.

### Fixed

- Child repo's `## Architecture diagram` section linked back to the org diagram with a malformed,
  non-resolving URL (missing GitHub's required `/blob/<branch>/` path segment); corrected to a
  relative link that resolves once merged into the instance repo.
- A model responding with prose reasoning instead of a JSON verdict crashed the doc-drift check
  outright with no recovery path — now corrected via retry (see agent-runtime, above).
- `instance_default_branch` resolution depended on `gh auth login` having been run interactively,
  a stricter precondition than the token-based auth the bootstrap script's own downloads already
  relied on successfully — a working `GH_TOKEN`/`GITHUB_TOKEN` now resolves it directly.
- The org diagram's links to each child repo's own diagram used the href `docs/{repo}/architecture.md`,
  but the org diagram file itself already lives inside `docs/`, so GitHub resolved that relative link
  to the non-existent `docs/docs/{repo}/architecture.md` — every such link 404'd. Corrected to the
  literal relative href `{repo}/architecture.md`.

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
  (exact command/skill per stale doc) in the GitHub Actions summary and PR comment; now also
  judges the architecture overview's `## Architecture diagram` section for staleness the same way
  as its prose.
- Initialization-time drift resolution: local agent runs revise documentation that contradicts the
  current repo state, recording what was resolved in `panopticon-changelog.md` rather than
  cluttering the docs themselves; genuinely ambiguous cases prompt the user instead of guessing.

**Architecture diagrams** (`architecture-diagrams`)
- Agent-drawn `## Architecture diagram` section in every repo's architecture overview — a
  component/data-flow diagram in the org's configured format (default Mermaid), grounded in the
  actual code, with a back-link to the org diagram.
- Deterministic, LLM-free org-wide diagram (`docs/architecture.md` in the instance repo): one
  section per repo with cross-repo interfaces, a relationship diagram, and an interface table,
  rebuilt on every merge to main directly from the compiled index so it can never disagree with
  it. Interfaces used only within a single repo are excluded from the org diagram.
- Diagram rendering format is configurable per instance (`panopticon.diagram.config.json`,
  default `mermaid`); an unsupported configured format fails loudly rather than silently skipping
  diagram generation.
- Navigation between the org diagram and per-repo diagrams uses plain markdown links, not
  diagram-native `click` directives, since GitHub does not reliably support Mermaid click-to-URL
  navigation.

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
- General protected-instance-local-config mechanism: `sync-from-template.yml` excludes registered
  paths (starting with `panopticon.diagram.config.json`) from its merge via a `.gitattributes`
  `merge=ours` driver, so an instance's customization always wins over what the template ships,
  and warns (non-blocking) when the template adds or removes a field the instance hasn't picked up.

**PR evaluation** (`pr-evaluation`)
- Reusable PR workflow: initialization check, doc-drift check, index-currency check, a
  deterministic diagram-existence check (architecture diagram section present and well-formed, no
  LLM call), pre-merge index simulation (dry-run over the same merge code path as the real merge),
  and `{repo}/{branch}` branch-state push to the instance repo.
- Org-configurable gating per check type (init/doc-drift blocking, interface-conflict and
  diagram-missing advisory, by default), read from the instance repo's `panopticon.config.json`
  rather than hardcoded.
- Combined report: a de-duplicated TL;DR leading (and trailing) the GitHub Actions summary and PR
  comment, collapsing every doc-drift/index-currency/diagram-existence finding into a single "run
  panopticon-doc-generation once" action regardless of how many docs, the index, or the diagram
  section are affected.
- CI checks distinguish an operational failure (crash, malformed LLM response, unreachable
  endpoint) from a genuine business verdict by a fixed exit-code contract, so a check that could
  not run is never silently misreported as passing or as a stale-docs finding — and every
  independent check still runs and reports its own outcome regardless of an earlier failure.

**Master sync** (`master-sync`)
- Merge-to-main sync workflow: docs copied to `docs/{repo}/`, index shard replaced wholesale,
  compiled index rebuilt, pushed directly to the instance repo's default branch (no PR).
- Deterministic org-wide architecture diagram rebuilt in the same commit as the compiled index,
  with no dependency on any child repo having a diagram section yet.
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

[0.1.3]: https://github.com/industrial-curiosity/panopticon-ay-eye/releases/tag/v0.1.3
[0.1.2]: https://github.com/industrial-curiosity/panopticon-ay-eye/releases/tag/v0.1.2
[0.1.1]: https://github.com/industrial-curiosity/panopticon-ay-eye/releases/tag/v0.1.1
[0.1.0]: https://github.com/industrial-curiosity/panopticon-ay-eye/releases/tag/v0.1.0
