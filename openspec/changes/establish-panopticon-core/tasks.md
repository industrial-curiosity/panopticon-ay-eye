## 1. Index core (interface-indexing)

- [x] 1.1 Define the JSON index schema (schema_version, keyed entries with consumer/producer repo-object
      lists, conflicts array) and write fixture files
- [x] 1.2 Implement index load/validate/save with stdlib-only Python (`panopticon/` package layout)
- [x] 1.3 Implement shard replace + deterministic compiled-index rebuild
- [x] 1.4 Implement entry matching and conflict detection (consumer match, owner match, conflict entries)
- [x] 1.5 Implement `simulate_merge` as a dry-run of the same merge code path, emitting a report structure
- [x] 1.6 Implement the parser registry (`detect`/`extract` contract) and the REST/OpenAPI starter parser
- [x] 1.7 Add the Kafka topic-config starter parser
- [x] 1.8 Implement deterministic name-normalization rules and `panopticon-` hint-comment parsing (hints
      honored first), applied at extraction and merge time so shards store canonical names and compile stays
      LLM-free
- [x] 1.9 Unit tests over fixtures: merge, compile reproducibility, conflict cases, simulation parity with merge

## 2. Agent runtime (agent-runtime)

- [x] 2.1 Implement the stdlib HTTP client (CI-only execution path) for OpenAI-compatible `/chat/completions`
      against `PANOPTICON_LLM_ENDPOINT` / `PANOPTICON_LLM_API_KEY`, with retry and timeout
- [x] 2.2 Implement skill loading (markdown instruction files → system prompt)
- [x] 2.3 Implement fail-loudly behavior when the endpoint or any other requirement is missing or unreachable
      (clear error naming what is missing and how to provide it)
- [x] 2.4 Tests with a stub HTTP server: request shape, retries, degradation paths

## 3. Extraction and doc generation (interface-indexing + doc-generation)

- [x] 3.1 Implement LLM extraction fallback: candidate-file selection, `extracted_by: llm` tagging, parser-gap
      recommendations in the workflow summary
- [x] 3.2 Write the harness-portable doc-generation skill files and templates for the four layers (architecture
      overview, per-component, interface, operational) — runnable in any agent harness and by the CI runtime
- [x] 3.3 Implement deterministic interface-doc rendering from the local index
- [x] 3.4 Implement doc regeneration in place, including removal of docs for deleted components
- [x] 3.5 Rewrote `panopticon/drift.py`'s `format_report()` to satisfy the strengthened "Doc-vs-code drift
      detection" requirement. Each stale-doc reason now gets a "How to fix" line, differentiated by doc
      type via a new `INTERFACE_DOC_SUFFIX = "interfaces.md"` constant: `interfaces.md` gets the specific
      `python3 -m panopticon.docs render --repo-name <repo> --index panopticon/index.json --docs-root
      <docs-location>` command (it's deterministically rendered, never agent-authored), while the other
      three layers get "run the panopticon-doc-generation skill in your agent." The report now ends with an
      explicit statement that the fix must be committed and pushed to this same PR's branch — not a new PR
      — and that the check re-runs automatically on that push. Added
      `test_stale_report_states_same_branch_push_and_rerun` and
      `test_stale_report_gives_interface_doc_specific_remediation` to `tests/test_drift.py`; the pre-existing
      `test_stale_report_names_docs_and_remediation` still passes unchanged. `docs/testing.md` updated. All
      197 tests pass.
- [x] 3.6 Write the interface naming/matching skill (LLM judgment layered over hints and normalization rules;
      persists judgments as `panopticon-interface` hint comments; local agents judge and write hints, CI fails
      on unresolvable names with an instruction to add a hint)
- [x] 3.7 Rewrote `panopticon-doc-generation/SKILL.md`'s rule 7 for the changed resolution mechanism: instead
      of a visible inline note in the revised doc's own prose, it now instructs appending an entry to a
      separate `panopticon-changelog.md` file in the docs location (created if absent), naming the doc, what
      was found, and how it was resolved — and explicitly never staging, committing, or pushing that file,
      leaving it for the user's own commit step. `panopticon-interface-naming/SKILL.md`,
      `panopticon-interface-extraction/SKILL.md`, and `panopticon-init/SKILL.md`'s prior additions were
      unaffected (none of them described the inline-note mechanism) and needed no changes.
      `docs/setup-guide.md`'s "Commit and push" section already mentions the changelog file. No test
      changes — skill-file instruction content has no pytest coverage anywhere in this repo. All 197 tests
      pass (markdown-only change, unaffected). Spec'd in `doc-generation/spec.md`'s "Initialization-time
      drift resolution" requirement.

## 4. Repo initialization (repo-initialization)

- [x] 4.1 Implement bootstrap installer script (`install.py` in the template repo root): stdlib-only Python,
      reads `PANOPTICON_INSTANCE` env var or prompts, downloads **only `panopticon-*` skills** from instance
      repo's `.agents/skills/` to child repo's `.agents/skills/`, downloads and wires the three caller
      workflows to `.github/workflows/`, runs org prerequisite verification (report-only), prints literal
      slash-command prompts — does NOT write `panopticon/config.json`
- [x] 4.7 Refactor `panopticon/init_repo.py` into a finalization-only step: remove workflow wiring (now
      handled by the bootstrap script), retain validation of agent-produced docs and index, write
      `panopticon/config.json` only after validation passes — keep as the last artifact created
- [x] 4.8 `agent_prompts()` now takes no arguments and prints exactly one prompt — the literal
      `/panopticon-init` invocation — instead of the previous 3 separate prompts (doc-generation,
      interface-naming/extraction, finalization command). No instance-slug interpolation is needed
      since `panopticon-init` self-discovers it from the wired caller workflow file. `main()`'s call
      site updated to `agent_prompts()`. `tests/test_install.py::TestAgentPrompts` rewritten for the
      single-prompt contract. `docs/testing.md` and `README.md` updated to match.
- [x] 4.9 Unit tests for the bootstrap installer: skill download, workflow wiring, idempotent re-run, env var
      vs prompt fallback, missing-prerequisite reporting; includes test that non-`panopticon-` skills are
      excluded and test that agent prompts contain literal slash commands (`/panopticon-doc-generation` etc.)
- [x] 4.10 Unit tests for the install.py self-bootstrapping path: `tests/test_install_self_bootstrap.py`
      runs `install.py` in real, isolated subprocesses (copied into an empty temp dir with no sibling
      `panopticon/` package, so the import genuinely fails there — mutating `sys.modules` in-process
      isn't safe alongside the rest of the suite). Covers: the top-level `except ModuleNotFoundError`
      block exits clearly naming `PANOPTICON_INSTANCE` and the export-and-pipe command when unset and
      non-interactive (including with piped stdin that carries real bytes); `_load_from_github` fetches
      `panopticon/__init__.py`/`panopticon/bootstrap.py` from a stubbed GitHub API, installs them into
      `sys.modules`, and the retry import succeeds end-to-end (verified by actually running the
      installed fake `main()`, proving relative imports resolve); an HTTP error during fetch exits with
      a clear message naming the failing path.
- [x] 4.11 Fix the bootstrap installer's workflow_ref default: `bootstrap.py::main` now falls back to the
      instance repo's default branch (`default_branch`, already resolved for skill/tree fetching) instead
      of a hardcoded `DEFAULT_WORKFLOW_REF = "v1"` tag when `panopticon.config.json` omits `workflow_ref`
      — no manual tagging step required to get started. The now-unused `DEFAULT_WORKFLOW_REF` constant was
      removed from `bootstrap.py`. `tests/test_install.py::TestMainWorkflowRefDefault` covers both the
      default-branch fallback and the org-configured-ref-is-respected case end-to-end through `main()`.
      Automated tag-based release versioning remains out of scope — deferred to a future change.
- [x] 4.2 Implement org-level secret and variable verification with actionable setup instructions (secrets
      `PANOPTICON_LLM_API_KEY`/`PANOPTICON_INSTANCE_TOKEN` and variables `PANOPTICON_LLM_ENDPOINT`/
      `PANOPTICON_LLM_MODEL` checked separately via the gh API; child repos need no per-repo configuration;
      missing items must not block local init steps). Token-aware: `check_prerequisites` (bootstrap.py)
      now returns `manual_verification_steps(org)` immediately when no token is resolved, instead of
      hitting the API and surfacing a generic failure — prints the web UI path and the equivalent
      `gh secret list --org` / `gh variable list --org` commands, naming all four required items, with no
      error framing (`main()` no longer applies "missing items" language to that path). `init_repo.py`'s
      `verify_org_secrets` got the same treatment for the `gh`-installed-but-unauthenticated case via
      `_manual_verification_message()`/`_check_gh_api_kind()`.
- [x] 4.6 Add test for missing org-level variable scenario: verify that `verify_org_secrets` reports a clear
      message with setup instructions when a variable such as `PANOPTICON_LLM_ENDPOINT` is absent (mirrors
      existing `test_missing_secret_reported_with_instructions`)
- [x] 4.3 Make re-initialization idempotent (update in place, no duplicates)
- [x] 4.4 Implement documentation-location adoption: existing docs adopted and aligned; otherwise prompt with
      `docs/` default; record the location in `panopticon/config.json`
- [ ] 4.5 Test initialization end-to-end against a sandbox child repo (blocked locally: needs a sandbox GitHub
      org/repo; unit coverage in `tests/test_init_repo.py` exercises the full local flow against a temp repo)
- [x] 4.15 Added per-file download progress reporting to the bootstrap installer: `download_skills`,
      `download_local_tooling`, and `wire_workflows` in `panopticon/bootstrap.py` each print a
      `  [n/total] <name>` line per file/module/workflow as it completes, before their existing summary
      line. Covered by `tests/test_install.py`'s `test_prints_per_file_progress` on all three functions
      (via `contextlib.redirect_stdout`).
- [x] 4.16 Fixed the finalization step's `workflow_ref` derivation. Removed the stale
      `DEFAULT_WORKFLOW_REF = "v1"` constant from `panopticon/config.py` entirely — `load_org_config()`'s
      `workflow_ref` key now defaults to `None` (this module has no network access, so it can't know the
      instance's true default branch). `panopticon/init_repo.py` gained `discover_workflow_ref(child_root)`
      (parses the ref from `.github/workflows/panopticon-pr.yml`'s `uses:...@ref` line) and
      `_fallback_workflow_ref(child_root)` (falls back to the child repo's checked-out git branch, or the
      literal `"main"` if that fails — never a hardcoded tag). `initialize()`'s and `main()`'s
      `workflow_ref`/`--workflow-ref` default changed from the removed constant to `None`, meaning
      "derive it" via those two functions; an explicit value can still override. Covered by
      `tests/test_init_repo.py`'s `TestDiscoverWorkflowRef`, `TestFallbackWorkflowRef`, and
      `TestWorkflowRefDefaultsToDiscovery`; `tests/test_config.py` updated for the new `None` default.
- [x] 4.17 Removed the stale `"workflow_ref": "v1"` from the template repo's root
      `panopticon.config.json` (committed 2026-07-04, before task 4.11 introduced the
      default-branch-fallback design). The file now contains only `gating` and `schema_version`,
      matching the setup guide's own example JSON. Added a regression test,
      `tests/test_config.py::test_template_root_config_ships_no_pinned_workflow_ref`, asserting the
      shipped root config has no `workflow_ref` key, so this fossil can't silently reappear.
- [x] 4.18 Added retry-with-backoff to `bootstrap.py`'s `_api_get` (previously: any `HTTPError` — transient
      or not — immediately raised and aborted the whole installer). Found via a real GitHub API `502`
      mid-install. Contributing factors identified during triage, not just "GitHub flakiness":
      `resolve_token()` silently falls back to unauthenticated requests when no `GH_TOKEN`/`GITHUB_TOKEN`/
      `gh auth` is available, and a full run fires 20+ sequential requests (`download_skills`,
      `download_local_tooling`, `wire_workflows`) with no pacing — both of which make transient
      rate-limit/gateway errors more likely. `_api_get` now retries `429`/`5xx` HTTP statuses and
      `urllib.error.URLError` connection failures up to 3 attempts with `2 ** (attempt - 1)`s backoff
      (mirroring `panopticon/llm.py`'s `LLMClient.chat()` pattern), via new optional `max_attempts`/`sleep`
      kwargs — purely additive, no existing caller changed. Non-transient errors (`401`/`403`/`404`) still
      fail on the first attempt, unchanged. 4 new tests in `tests/test_install.py::TestApiGetRetry`
      (transient-retried-and-succeeds, retries-exhausted-then-raises, non-transient-fails-immediately,
      connection-error-retried) using an injected fake `sleep`. All 195 tests pass. `docs/testing.md`
      updated. Spec'd in `repo-initialization/spec.md`'s "GitHub API request resilience" requirement.
- [x] 4.12 Third implementation, per explicit user request rejecting the two-script design. Removed
      `panopticon/configure_ides.py` and `tests/test_configure_ides.py` entirely. `bootstrap.py` now
      does it all inline: `TOOL_LOCATIONS` (per-tool location table mirroring
      `docs/agentskills-support.md`), `candidate_locations()`, `compatibility_table_lines()` (printed
      before prompting), `_detect_existing_location()` (idempotent re-run — reuses a previously chosen
      location without re-prompting), `_resolve_typed_answer()`, `_apply_key()` (pure arrow-key state
      transition), `_arrow_key_menu()` (raw `termios`/`tty` mode reading `/dev/tty`, so piped
      `curl | python3` can still prompt since stdin is only consumed by the script content, not
      `/dev/tty`), `_tty_typed_prompt()` (fallback when raw mode isn't available),
      `select_skills_location()` (orchestrates: env override → existing-location reuse → arrow-key menu
      → typed `/dev/tty` prompt → plain `input()` if stdin is itself a tty → silent
      `.agents/skills` default). `download_skills()` takes a `dest_location` parameter — skills are
      downloaded only after `select_skills_location()` runs, never unconditionally to
      `.agents/skills/`. `agent_prompts()` back to 3 prompts, no configuration-script step.

      Found and fixed a real hang: `_arrow_key_menu`'s cleanup used `termios.tcsetattr(fd,
      termios.TCSADRAIN, ...)`, which blocks draining pending output if nothing reads the pty's other
      end — reproduced with a real pty pair, fixed by switching to `TCSANOW`. Verified via a pty-pair
      unit test (`TestArrowKeyMenu`) and a full end-to-end `main()` smoke test through a real pty
      (arrow-key selection → skills written only to the chosen location). `tests/test_install.py`
      rewritten: `TestCandidateLocations`, `TestDetectExistingLocation`, `TestResolveTypedAnswer`,
      `TestApplyKey`, `TestArrowKeyMenu`, `TestSelectSkillsLocation`, `TestMainSkillsLocationFlow`. All
      170 tests pass. `docs/testing.md` updated; `docs/setup-guide.md`/`docs/agentskills-support.md`
      already matched (written during the correction-sweep session) — verified no stale references
      remain.
- [x] 4.13 Vendor the local-tooling subset of the `panopticon` package into the child repo during
      bootstrap. Added `LOCAL_TOOLING_MODULES = ("__init__.py", "config.py", "docs.py", "index.py",
      "init_repo.py")` and `download_local_tooling()` in `panopticon/bootstrap.py`, wired into `main()`
      as a new step right after skills download and before workflow wiring — writes the five files to
      the child repo's `panopticon/` directory, overwriting in place on re-run (same pattern as
      `download_skills`). CI-only modules (`llm.py`, `drift.py`, `currency.py`, `merge.py`,
      `extraction.py`, `skills.py`, `bootstrap.py`, `parsers/`) are never requested — enforced by a test
      stub that raises on any unrecognized URL. Updated `panopticon/__init__.py`'s module docstring to
      document the CI-only vs. vendored-locally split. `tests/test_install.py::TestDownloadLocalTooling`
      plus updated `main()`-level routers and a new end-to-end assertion
      (`test_local_tooling_vendored_alongside_skills`). All 179 tests pass. Verified end-to-end with a
      real subprocess serving this repo's actual `panopticon/*.py` content: bootstrapped an isolated
      temp child repo, then ran `python3 -m panopticon.docs validate` there with no `PYTHONPATH` set —
      it imported and ran successfully (reporting a real missing-docs validation failure, not an import
      crash), directly reproducing and confirming the fix for the reported bug. `docs/testing.md`
      updated.
- [x] 4.14 Write the `panopticon-init` orchestrating skill at `.agents/skills/panopticon-init/SKILL.md`
      (the `panopticon-` prefix means the existing skill-download step ships it with no bootstrap.py
      changes needed). Instructs the agent to run, in order: `panopticon-interface-naming`,
      `panopticon-interface-extraction`, `panopticon-doc-generation`, then the finalization command with
      the instance slug self-discovered from the `uses:` line in `.github/workflows/panopticon-pr.yml`
      (regex/parse `owner/repo` out of `uses: owner/repo/.github/workflows/...@ref`). Maintains a
      checkpoint log at `panopticon/.init-log.json` (a JSON list of completed step ids) — read before
      each step to skip already-completed ones, updated after each step completes, deleted once all four
      steps are done and `panopticon/config.json` exists. Fixes the ordering bug a user hit directly:
      doc-generation was being run before the index existed to render `interfaces.md` from.

## 5. Instance repo structure and config

- [x] 5.1 Define the instance repo layout (`docs/{repo}/`, `interfaces/`, `panopticon.config.json`); marking
      the repo as a GitHub template repository is a manual owner step documented in the setup guide
- [x] 5.2 Implement `panopticon.config.json` reading (gating modes per check type, workflow ref policy) with
      per-check defaults: init and doc-drift fail, interface-conflict advisory

## 6. PR evaluation workflows (pr-evaluation)

- [x] 6.1 Write the reusable PR workflow: initialization check with skip-and-instruct behavior
- [x] 6.2 Add the doc-drift check step with PR comment output, failing by default when docs are stale
- [x] 6.3 Add pre-merge simulation: index-currency check (CI agent evaluates the diff plus minimal context),
      fetch compiled index via `PANOPTICON_INSTANCE_TOKEN`, dry-run merge, PR comment + CI summary
- [x] 6.4 Add the `{repo}/{branch}` state push to the instance repo
- [x] 6.5 Wire gating configuration into check outcomes (per-check defaults, org overrides in both directions)
- [ ] 6.6 Test the PR workflow in a sandbox org (conflict PR, clean PR, uninitialized repo) (blocked locally:
      needs a sandbox GitHub org; the Python CLIs the workflow invokes are unit-tested)
- [x] 6.7 Fixed a real bug found during the first live sandbox PR (task 6.6): the doc-drift check failed
      with "No module named panopticon.drift" and a missing report file. Root cause: `panopticon-pr.yml`'s
      checks run `python3 -m panopticon.<mod>`/`-c "from panopticon.<mod> import ..."` with the child repo
      as the working directory and `PYTHONPATH` pointing at the checked-out instance repo — but `python3
      -m`/`-c` prepend the current directory to `sys.path` *ahead of* `PYTHONPATH`, so the child repo's
      vendored local-tooling subset (task 4.13's `LOCAL_TOOLING_MODULES` — no `drift.py`/`currency.py`/
      `merge.py`) silently shadowed the instance repo's full copy for every CI-only module. Reproduced
      locally (`python3 -m panopticon.drift` against a stand-in child+instance directory pair raised the
      identical error), then fixed by setting `PYTHONSAFEPATH: "1"` at job level in `panopticon-pr.yml`
      (disables the cwd-prepend; verified `ubuntu-latest` ships Python 3.12.3, above the 3.11 minimum for
      this flag). The same latent shadowing existed in the gating-config and empty-index-check steps too,
      just harmlessly, because `config.py`/`index.py` happen to exist in both copies — those are now
      guaranteed to resolve from the instance repo as well. Added the same `PYTHONSAFEPATH: "1"` to
      `panopticon-merge.yml` (see 7.6) since it shares the identical child+instance+`PYTHONPATH` pattern,
      even though its one `python3 -m panopticon.merge` call wasn't hit by this bug (it already `cd`s into
      the instance dir first, aligning cwd with `PYTHONPATH`). Spec updated:
      `repo-initialization/spec.md`'s "Local tooling package vendored into child repo" requirement now
      states this resolution guarantee explicitly, with a new scenario. No unit test covers this (it's a
      CI-YAML-only fix); all 191 existing unit tests still pass unaffected.
- [x] 6.8 Collapsed the TL;DR further per user feedback on a real report (6 separate bullets: 1
      index-update line + 5 per-doc "run panopticon-doc-generation" lines). `panopticon/report.py`'s
      `update_index` and `regenerate_doc` action kinds are now one `run_doc_generation` kind (no
      `target` — it always means "run the whole skill once"); `_ACTION_ORDER`/`_TEMPLATES` and the
      module docstring updated accordingly. `drift.py`'s and `currency.py`'s `collect_actions()` now
      return exactly `[{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}]` when stale,
      regardless of how many docs are stale or which ones — no more per-doc targets.
      `resolve_conflict`/`commit_and_push` untouched. Rewrote the broken assertions in
      `tests/test_report.py`, `tests/test_drift.py`, `tests/test_currency.py` (217 tests total, up
      from 215 — 2 new tests covering the exact collapse scenario and that conflicts stay separate).
      Verified directly: drift+currency actions together now render as exactly 2 TL;DR lines.
      `docs/testing.md` corrected (still referenced the old two-kind names). Spec'd in
      `pr-evaluation/spec.md`'s "Combined report leads with a de-duplicated action list" requirement.

## 7. Master sync workflows (master-sync)

- [x] 7.1 Write the reusable merge-to-main workflow: docs copy, shard replace, compiled rebuild, direct push
- [x] 7.2 Implement the fetch-rebase-retry loop for concurrent pushes
- [x] 7.3 Implement conflict-issue creation in both repos with cross-links, updating at most one open issue
      per child repo in each repository
- [x] 7.4 Write the PR-close workflow deleting the matching `{repo}/{branch}` instance branch
- [ ] 7.5 Test merge sync in the sandbox org (clean merge, conflicting merge, concurrent merges) (blocked
      locally: needs a sandbox GitHub org; merge/retry logic is unit-tested via the merge CLI)
- [x] 7.6 Added `PYTHONSAFEPATH: "1"` at job level in `panopticon-merge.yml`, matching the fix in 6.7 —
      same child+instance-repo+`PYTHONPATH` pattern as `panopticon-pr.yml`, hardened defensively even
      though this workflow's one `python3 -m panopticon.merge` call already `cd`s into the instance dir
      before running, so it wasn't actually hit by the shadowing bug.

## 8. Documentation

- [x] 8.3 Ship `sync-from-template.yml` in the template repo: manual-trigger workflow that detects missing
      common ancestor (first sync after "Use this template") and resolves add/add conflicts with `-X theirs`
      automatically; subsequent syncs use normal merge strategy and surface genuine conflicts for manual resolution
- [x] 8.1 Write template-repo docs: org-owner setup guide (create instance from template, secrets, variables,
      config) and parser contribution guide
- [x] 8.2 Update README.md and docs/FUSE Panopticon Strategy.md to reflect any user-facing or architectural
      changes introduced by this change
