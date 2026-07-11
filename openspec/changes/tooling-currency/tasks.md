## 1. Org-declared protected-paths config

- [ ] 1.1 Add `protected_paths` to `panopticon/config.py`'s org config schema: a list of non-empty
      path strings, default empty list, validated by `load_org_config()`

## 2. `.git/info/attributes` regeneration (`sync-from-template.yml`)

- [ ] 2.1 Add a step, run before the existing merge step, that reads `protected_paths` (via
      `load_org_config`) and writes each path with the `merge=ours` attribute to
      `.git/info/attributes` — never the tracked `.gitattributes`, no commit. Confirm the existing
      `git config merge.ours.driver true` registration covers both the template-declared
      (`PROTECTED_CONFIG_FILES`, tracked `.gitattributes`) and org-declared (`protected_paths`,
      `.git/info/attributes`) paths with the same single driver
- [ ] 2.2 In the same step, print every protected path to `$GITHUB_STEP_SUMMARY`
- [ ] 2.3 Verify end-to-end in a sandbox instance/template repo pair (mirroring the design.md
      spike): an org-declared protected path survives both the first-sync (`-X theirs`,
      `--allow-unrelated-histories`) and routine-sync paths, including when the incoming template
      commit also modifies that same path in the same run, and that the merge never aborts and the
      tracked `.gitattributes` merges normally throughout

## 3. Tooling-currency check module (CI-only, not vendored)

- [ ] 3.1 Create `panopticon/tooling_currency.py` with a workflow-ref check: resolve the child's
      wired `uses:@ref` via `git ls-remote origin <ref>` against the instance checkout's current
      `HEAD` commit; return a finding when they differ or the ref doesn't resolve, nothing
      otherwise
- [ ] 3.2 Add a skills/tooling drift check: content-diff `.panopticon-instance/.agents/skills/panopticon-*`
      against the child's skills location (detected via `bootstrap._detect_existing_location()`,
      not a new persisted config field) and `.panopticon-instance/panopticon/{LOCAL_TOOLING_MODULES}`
      against the child's `panopticon/`; return one finding per differing/missing/extra file
- [ ] 3.3 Add a `main()` CLI that prints one `::warning::` per finding from both checks and always
      exits `0` — this module never gates, so it has no business-verdict exit-code contract like
      drift.py/currency.py/diagram_check.py do

## 4. Wire the tooling-currency check into `panopticon-pr.yml`

- [ ] 4.1 Add a step after the instance-repo checkout that runs
      `python3 -m panopticon.tooling_currency`, printing its warnings to the step summary
- [ ] 4.2 Confirm this step's outcome is never read by the "Apply gating" step and never feeds
      `panopticon/report.py`'s combined TL;DR report — it is fully independent of both

## 5. Local sync script

- [ ] 5.1 Create `panopticon/sync.py`: default behavior fetches the instance repo's current
      default-branch skills and vendored tooling (reusing `bootstrap.py`'s `download_skills`/
      `download_local_tooling`) and overwrites the child repo's copies unconditionally — no
      per-file protection at the child layer
- [ ] 5.2 Add `--check-updates`: a pure dry run using a git-blob-sha comparison (GitHub tree API's
      per-file `sha` vs. a locally computed `sha1(f"blob {len(data)}\0".encode() + data)`, verified
      to reproduce `git hash-object`'s output) — reports which files would change, writes nothing
- [ ] 5.3 Add `sync.py` to `LOCAL_TOOLING_MODULES` in `bootstrap.py` so it's vendored into any
      already-bootstrapped child repo

## 6. Tests

- [ ] 6.1 Unit tests for `protected_paths`'s config schema (default, validation, round-trip)
- [ ] 6.2 Integration tests (real git repos via `subprocess`/`tempfile`, mirroring the design.md
      spike, not mocked) for the `.git/info/attributes` regeneration: protection holds across
      first-sync, routine-sync, and the same-path-conflict case; the merge never aborts; the tracked
      `.gitattributes` is unaffected
- [ ] 6.3 Unit tests for `panopticon/tooling_currency.py`'s ref-resolution and drift-diff logic
      (stubbed subprocess/filesystem) and its warning-format output
- [ ] 6.4 Unit tests for `panopticon/sync.py`'s default-overwrite and `--check-updates` dry-run
      behavior (stubbed GitHub API, mirroring `test_install.py`'s patterns), including a
      git-blob-sha correctness check against a known `git hash-object` value

## 7. Documentation

- [ ] Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
