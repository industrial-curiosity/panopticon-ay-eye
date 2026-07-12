## 1. Org-declared protected-paths config

- [x] 1.1 Add `protected_paths` to `panopticon/config.py`'s org config schema: a list of non-empty
      path strings, default empty list, validated by `load_org_config()`

## 2. `.git/info/attributes` regeneration (`sync-from-template.yml`)

- [x] 2.1 Add a step, run before the existing merge step, that reads `protected_paths` (via
      `load_org_config`) and writes each path with the `merge=ours` attribute to
      `.git/info/attributes` — never the tracked `.gitattributes`, no commit. Confirm the existing
      `git config merge.ours.driver true` registration covers both the template-declared
      (`PROTECTED_CONFIG_FILES`, tracked `.gitattributes`) and org-declared (`protected_paths`,
      `.git/info/attributes`) paths with the same single driver
- [x] 2.2 In the same step, print every protected path to `$GITHUB_STEP_SUMMARY`
- [x] 2.3 Verified end-to-end via the real-git-repo integration tests in `tests/test_sync_from_template.py`
      (group 6.2, mirroring the design.md spike as permanent, repeatable coverage rather than a
      one-off manual sandbox run): an org-declared protected path survives both the first-sync
      (`-X theirs`, `--allow-unrelated-histories`) and routine-sync paths, including when the
      incoming template commit also modifies that same path in the same run, and the merge never
      aborts and the tracked `.gitattributes` merges normally throughout — all three tests pass

## 3. Tooling-currency check module (CI-only, not vendored)

- [x] 3.1 Create `panopticon/tooling_currency.py` with a workflow-ref check: resolve the child's
      wired `uses:@ref` via `git ls-remote origin <ref>` against the instance checkout's current
      `HEAD` commit; return a finding when they differ or the ref doesn't resolve, nothing
      otherwise
- [x] 3.2 Add a skills/tooling drift check: content-diff `.panopticon-instance/.agents/skills/panopticon-*`
      against the child's skills location (detected via `bootstrap._detect_existing_location()`,
      not a new persisted config field) and `.panopticon-instance/panopticon/{LOCAL_TOOLING_MODULES}`
      against the child's `panopticon/`; return one finding per differing/missing/extra file
- [x] 3.3 Add a `main()` CLI that prints one `::warning::` per finding from both checks and always
      exits `0` — this module never gates, so it has no business-verdict exit-code contract like
      drift.py/currency.py/diagram_check.py do

## 4. Wire the tooling-currency check into `panopticon-pr.yml`

- [x] 4.1 Add a step after the instance-repo checkout that runs
      `python3 -m panopticon.tooling_currency` — findings surface as `::warning::` annotations
      (the same mechanism every other advisory message in this codebase uses; no separate
      `$GITHUB_STEP_SUMMARY` write needed, matching the existing protected-config field-diff step)
- [x] 4.2 Confirm this step's outcome is never read by the "Apply gating" step and never feeds
      `panopticon/report.py`'s combined TL;DR report — it is fully independent of both

## 5. Local sync script

- [x] 5.1 Create `panopticon/sync.py`: default behavior fetches the instance repo's current
      default-branch skills and vendored tooling and overwrites the child repo's copies
      unconditionally — no per-file protection at the child layer. Duplicates (rather than
      imports) bootstrap.py's `download_skills`/`download_local_tooling`/GitHub-API helpers: since
      sync.py is itself vendored into the child repo but bootstrap.py is explicitly CI-only and
      never vendored, `from .bootstrap import ...` raised `ModuleNotFoundError` the moment sync.py
      actually ran from a real child repo (caught post-implementation, running the vendored script
      by hand) — fixed by making sync.py self-contained, mirroring this codebase's existing
      `ORG_SECRETS`/`ORG_VARS` duplication precedent across the same CI/local module boundary in
      `init_repo.py`. `test_sync.py::TestSelfContained` guards against the duplicated constants
      drifting from bootstrap.py's copies.
- [x] 5.2 Add `--check-updates`: a pure dry run using a git-blob-sha comparison (GitHub tree API's
      per-file `sha` vs. a locally computed `sha1(f"blob {len(data)}\0".encode() + data)`, verified
      to reproduce `git hash-object`'s output) — reports which files would change, writes nothing
- [x] 5.3 Add `sync.py` to `LOCAL_TOOLING_MODULES` in `bootstrap.py` so it's vendored into any
      already-bootstrapped child repo

## 6. Tests

- [x] 6.1 Unit tests for `protected_paths`'s config schema (default, validation, round-trip)
- [x] 6.2 Integration tests (real git repos via `subprocess`/`tempfile`, mirroring the design.md
      spike, not mocked) for the `.git/info/attributes` regeneration: protection holds across
      first-sync, routine-sync, and the same-path-conflict case; the merge never aborts; the tracked
      `.gitattributes` is unaffected
- [x] 6.3 Unit tests for `panopticon/tooling_currency.py`'s ref-resolution and drift-diff logic
      (stubbed subprocess/filesystem) and its warning-format output
- [x] 6.4 Unit tests for `panopticon/sync.py`'s default-overwrite and `--check-updates` dry-run
      behavior (stubbed GitHub API, mirroring `test_install.py`'s patterns), including a
      git-blob-sha correctness check against a known `git hash-object` value

## 7. Documentation

- [x] Update README.md and docs/spec.md to reflect any user-facing or architectural changes
      introduced by this change (this repo has no `docs/spec.md`; README.md is the closest
      architecture doc and was updated, along with `docs/setup-guide.md` and `docs/testing.md` per
      the proposal's explicit documentation requirement)

## 9. Getting-started guide (`PANOPTICON.md`)

- [x] 9.1 Author `PANOPTICON.md` at the template repo root: concise, static content covering the
      three repo roles/lifecycle, where architecture diagrams live (this repo's own diagram section
      and the instance repo's org-wide `docs/architecture.md`), and the literal
      `python3 -m panopticon.sync` / `--check-updates` commands
- [x] 9.2 Add a download step to `panopticon/bootstrap.py`'s `main()` that fetches `PANOPTICON.md`
      from the instance repo and writes it to the child repo's root, overwritten idempotently on
      re-run (same trust model as skills/tooling)
- [x] 9.3 Update `bootstrap.py`'s printed output so every run (first bootstrap and re-run alike)
      names `PANOPTICON.md`'s location and the literal `python3 -m panopticon.sync` command,
      independent of the `/panopticon-init` agent prompt
- [x] 9.4 Unit tests: `PANOPTICON.md` is downloaded on first run and overwritten (not duplicated) on
      re-run; bootstrap's printed output contains both the guide's location and the sync command on
      both first-run and re-run

## 10. Cross-repo diagram link fix

- [x] 10.1 Fix `.agents/skills/panopticon-doc-generation/SKILL.md` and
      `assets/architecture-template.md`'s org-diagram back-link instructions: replace the malformed
      bare-URL prose with the relative markdown link `[org diagram](../architecture.md#{repo})`
      (`{repo}` from `panopticon/config.json`'s existing `repo` field — no new config field needed),
      and note explicitly that this link resolves once the file is merged into the instance repo at
      `docs/{repo}/architecture.md`, not when viewed directly in the child repo
- [x] 10.2 Verify the already-relative same-repo diagram links in `panopticon/diagrams.py`
      (`docs/{other}/architecture.md`, `docs/{repo}/architecture.md`) remain unchanged and correct —
      no code change expected here, confirmed via existing `tests/test_diagrams.py` coverage
      (13/13 passing, `panopticon/diagrams.py` untouched this session)

## 11. instance_default_branch and the org-diagram link script

> Note: 11.1, 11.2, and 11.4 were cleared and reopened after a real-world usability report:
> `_resolve_instance_default_branch`'s original implementation used `gh api ... ` as a subprocess,
> which depends on `gh auth login` having been run interactively — a *different*, narrower
> precondition than the token-based mechanism `bootstrap.py`/`sync.py` already use successfully for
> every other instance-repo request. A user whose bootstrap run succeeded (proving their token-based
> auth worked) still hit "gh CLI isn't authenticated" from finalization, and had no way to recover
> without fixing `gh` specifically. See design.md D11. The code these tasks originally produced is
> directly incompatible with the corrected spec and needs to change, not just be redescribed — hence
> clearing rather than leaving checked.

- [x] 11.1 Rewrite `panopticon/init_repo.py`'s `_resolve_instance_default_branch` to use the same
      token/transport mechanism `bootstrap.py`/`sync.py` already use (`GH_TOKEN`/`GITHUB_TOKEN` env
      vars, falling back to `gh auth token` only to extract a token — never a direct `gh api`
      subprocess call), duplicating the needed primitives the same way `sync.py` already does (task
      5.1's `ModuleNotFoundError` lesson: `init_repo.py` is vendored and cannot import
      `bootstrap.py`). Still: never hardcode `"main"`, never derive from `workflow_ref`; omit the
      field with an explanatory message when genuinely unresolvable.
- [x] 11.2 Add the same corrected resolution logic to `panopticon/bootstrap.py`
      (`fetch_instance_default_branch`, reusing its existing `_api_get`), and call it from `main()`
      via `refresh_instance_default_branch`: when `panopticon/config.json` already exists (repo
      already initialized), re-resolve `instance_default_branch` and update just that field in
      place — every other field untouched. Bootstrap still never *creates*
      `panopticon/config.json` (see "Bootstrap script refreshes instance_default_branch on rerun")
- [x] 11.3 Add `org_diagram_link.py` to `LOCAL_TOOLING_MODULES` in `bootstrap.py` so it's vendored
      into any already-bootstrapped child repo. `panopticon/tooling_currency.py`'s drift check
      imports `LOCAL_TOOLING_MODULES` from `bootstrap.py` directly, so it picks this up
      automatically — no separate change needed there. `panopticon/sync.py` cannot import from
      `bootstrap.py` (see task 5.1's `ModuleNotFoundError` lesson) and duplicates its own copy of
      `LOCAL_TOOLING_MODULES`, so that duplicated tuple got the same addition, kept in sync via
      `test_sync.py::TestSelfContained.test_local_tooling_modules_matches_bootstrap` (still passing).
      `panopticon/__init__.py`'s docstring updated too. All existing tests pass unchanged — the
      `_router()` stubs in test_install.py/test_sync.py iterate `LOCAL_TOOLING_MODULES` dynamically.
      (Unaffected by the D11 rework — stays complete.)
- [x] 11.4 Update `panopticon/org_diagram_link.py`: config field checked first as before (no network
      call in the common case, `resolve_branch()`); when `instance_default_branch` is genuinely
      absent, attempt a live GitHub API lookup (same token-based mechanism as 11.1, duplicated
      again per the "each vendored module stands alone" precedent) before failing; if that also
      fails, fail loudly with a message explaining both why (config gap + live lookup failure) and
      how to fix it — never guessing a branch name. `build_link()`'s signature changed from
      `build_link(repo_config)` to `build_link(instance, branch, repo)` to separate URL construction
      from branch resolution.
- [x] 11.5 Unit tests: `_resolve_instance_default_branch`'s corrected token-based resolution
      (`GH_TOKEN`/`GITHUB_TOKEN` succeed without `gh auth login`; `gh auth token` fallback; still
      returns `None`, never a guess, when nothing works) in both `init_repo.py` and `bootstrap.py`;
      bootstrap's rerun-refresh (updates only `instance_default_branch`, leaves other fields
      untouched, never creates `panopticon/config.json` on a first run — new
      `TestFetchInstanceDefaultBranch`/`TestRefreshInstanceDefaultBranch` in `test_install.py`, plus
      an end-to-end `main()` test for the rerun case); `org_diagram_link.py`'s live fallback
      (succeeds via live lookup when config is missing the field; fails loudly, still no guessed
      branch, when the live lookup also fails) — rewritten `tests/test_init_repo.py`,
      `tests/test_install.py`, `tests/test_org_diagram_link.py`. Also fixed a pre-existing bug in
      `test_init_repo.py` (`unittest.mock` used but never imported at module scope — worked only by
      accident when run alongside other files that happened to import it first), and a
      `ResourceWarning` from unclosed `HTTPError` objects in the three duplicated resolvers (fixed
      to match `bootstrap.py`'s existing `_api_get`'s `with exc:` cleanup pattern). Full suite:
      351/351 passing, including with `ResourceWarning` promoted to an error.
