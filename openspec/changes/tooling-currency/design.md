## Context

Three different things can drift between a child repo and its instance repo, and none of them are
currently checked:

1. **Wired workflow ref** — the `uses: <instance>/.github/workflows/panopticon-pr.yml@<ref>` line
   `install.py`'s `wire_workflows()` writes into each child repo's three caller workflows.
2. **Downloaded skills** — `panopticon-*` files under whatever location `install.py` chose
   (`.agents/skills/` by default; see `docs/agentskills-support.md`).
3. **Vendored local tooling** — `panopticon/{__init__,config,docs,index,init_repo}.py`
   (`bootstrap.py`'s `LOCAL_TOOLING_MODULES`), downloaded so `python3 -m panopticon.docs` etc. work
   with no instance clone.

All three are snapshots taken once, at bootstrap time. `install.py` is safe to re-run and will
refresh all three (`bootstrap.py`'s own header comment: "Re-run install.py to update"), but nothing
prompts anyone to do so, and nothing checks whether they should. `docs/planned-work.md` already
names this gap.

Separately, an org may customize a `panopticon-*` skill or tooling module **at the instance repo
level** — this needs to survive `sync-from-template.yml`'s pull from the upstream template. This
reuses and generalizes the protected-config primitive `architecture-diagrams` built for
`panopticon.diagram.config.json` (design D7 of that change): a registry of paths excluded from the
template merge via `.gitattributes`' `merge=ours` + `git config merge.ours.driver true`. That
registry is template-declared and fixed (one entry today). Org-level skill/tooling customization is
the opposite shape: variable, per-org, and unknowable to the template in advance.

## Goals / Non-Goals

**Goals:**

- A deterministic, always-advisory PR check that warns when a child repo's wired workflow ref no
  longer resolves to the instance repo's current default-branch tip, or when its skills/vendored
  tooling differ in content from the instance repo's current copies.
- A local script, available in any already-bootstrapped child repo, that pulls the instance's
  current skills and tooling on demand — unconditional overwrite by default, with a `--check-updates`
  dry-run mode that reports without writing.
- A general mechanism for org-declared instance-level customization protection (skills, tooling,
  and future plugin content) that requires no commits and can never abort a `sync-from-template`
  merge, with a clear audit trail even though the protection itself leaves no trace in the tracked
  tree.

**Non-Goals:**

- Not gated, ever. This check has no `CHECK_TYPES`/gating entry and will never fail a workflow —
  explicit product decision ("handled at the child repo maintainer's discretion"), not a rollout
  stage to later escalate the way `diagram-missing` was.
- Not versioning workflow *content*. Child-repo workflows remain thin `uses:@ref` pointers, not
  copied files — "workflows once they're versioned" is a hypothetical future architecture this
  design does not build toward. The ref-alignment check treats the wired ref as a single string to
  resolve and compare, nothing more.
- Not migrating the existing `PROTECTED_CONFIG_FILES` / tracked-`.gitattributes` mechanism.
  `panopticon.diagram.config.json`'s protection keeps working exactly as built.
- Not unifying CI-mode and local-mode drift detection into one shared implementation. They compare
  fundamentally different things (two already-local trees vs. a local tree against a GitHub API
  response) and are deliberately two separate implementations (design D2).
- Not building a plugin system. `protected_paths` is shaped so a future plugin's protected content
  can be added to the same list later, but plugins themselves are out of scope here.

## Decisions

### D1: Workflow-ref alignment — resolve-and-compare-commits, not tag enumeration

**Decision**: the CI check resolves the child's wired ref to a commit via
`git -C .panopticon-instance ls-remote origin <ref>` and compares it to
`git -C .panopticon-instance rev-parse HEAD` — the commit the existing "Check out instance repo"
step already lands on, since that step passes no `ref:` override and therefore checks out the
default branch tip by construction. Equal → silent. Different, or the ref doesn't resolve at all
(deleted tag/branch) → `::warning::`.

This needs no tag history, no `fetch-depth`/`fetch-tags` changes to the existing checkout step
(`ls-remote` talks to the remote directly, independent of local clone depth), and no knowledge of
the default branch's *name* — the already-checked-out commit *is* the answer.

*Alternative considered*: enumerate all tags, find the "latest" one, compare against that too.
Rejected per explicit direction — adds tag-sorting semantics (chronological? semver? what if an
org never tags at all?) for no benefit over "does the wired ref currently match the default
branch tip," which is the actual regression this check protects against (an org bumps
`workflow_ref` and a child repo's caller workflow never gets re-wired to follow).

### D2: Skills/tooling drift — CI diffs local trees directly; the local script hits the GitHub API

**Decision**: two separate implementations, not one shared module:

- **CI** (`panopticon-pr.yml`): the instance repo is already checked out to `.panopticon-instance`
  for doc-drift/currency/simulation. The check is a plain recursive diff between
  `.panopticon-instance/.agents/skills/panopticon-*` and the child's own skills location, and
  between `.panopticon-instance/panopticon/{LOCAL_TOOLING_MODULES}` and the child's `panopticon/`.
  No network calls beyond the checkout that already happens. The child's skills location is found
  by reusing `bootstrap.py`'s existing `_detect_existing_location()` (via
  `python3 -c "from panopticon.bootstrap import _detect_existing_location; ..."` against
  `.panopticon-instance` on `PYTHONPATH`, the same resolution mechanism `drift.py`/`currency.py`/
  `merge.py`/`diagram_check.py` already rely on) — no new persisted `skills_location` config field
  needed; the heuristic that already picks the location at bootstrap time can re-derive it.
- **Local script**: no instance clone exists on a dev machine by design (`bootstrap.py`'s explicit
  "no local instance clone required" constraint). It must hit the GitHub contents/tree API, exactly
  as `install.py` already does for the initial download.

*Alternative considered*: timestamps. Rejected — CI checkout mtimes reflect checkout time, not
commit time, and local clones don't preserve historical mtimes either; comparing them would be
comparing noise, not staleness. Content comparison is the only sound signal, and it's already
available for free: GitHub's tree API returns a git blob `sha` per file (`bootstrap.py`'s
`_fetch_tree`), and CI already has both trees locally with no hashing needed at all.

### D3: Never gated

**Decision**: no `diagram-missing`-style advisory→blocking rollout. This check has no entry in
`panopticon.config.py`'s `CHECK_TYPES`/`DEFAULT_GATING`, ever. It always emits `::warning::`
(visible in the step summary and as inline PR annotations, same mechanism every other advisory
message in this codebase already uses — no new output channel).

*Alternative considered*: add `tooling-stale` to `CHECK_TYPES` defaulting to `advisory`, mirroring
every other check. Rejected per explicit direction: "handled at the child repo maintainer's
discretion" describes a check that is *never* meant to block, not one on a path toward blocking —
folding it into the gating lever would misrepresent that as a temporary rollout stage.

### D4: Reported standalone, not folded into the combined report

**Decision**: this check's warnings are plain `::warning::` lines, separate from
`panopticon/report.py`'s combined TL;DR report (which doc-drift, index-currency,
diagram-existence, and pre-merge simulation all feed into).

*Alternative considered*: add a new action kind to `report.py`'s `_TEMPLATES` (e.g.
`run_sync_script`) so a stale-tooling finding shows up in the TL;DR alongside stale docs. Rejected
— that report's contract is specifically "concrete actions a developer must take to resolve
everything the checks found" before merge; this check is explicitly not a gate and nothing here
needs resolving before merge. Mixing an FYI into a must-fix list would misrepresent both.

### D5: Local sync script — unconditional overwrite by default; `--check-updates` is a pure dry run

**Decision**: a new `panopticon/sync.py`, vendored into `LOCAL_TOOLING_MODULES` so it's available
in any already-bootstrapped child repo via `python3 -m panopticon.sync`. Default behavior
overwrites the child's skills and vendored tooling unconditionally from the instance's current
default branch — no protection layer at the child level, git review is the safety net (an
uncommitted or already-committed change the sync overwrites is visible in `git diff`/`git status`
before the user commits; anything they disagree with, they simply don't commit or hand-edit
afterward). `--check-updates` makes the *entire* run a dry run: it reports which files would
change (via git-blob-sha comparison — confirmed `sha1(f"blob {len(data)}\0".encode() + data)`
reproduces `git hash-object`'s output exactly) and writes nothing at all.

*Alternative considered*: protect customized files at the child layer too (mirroring the
instance-level protection in D6). Rejected per explicit direction — customization is meant to
happen once, at the instance level; child repos are meant to be uniform, disposable mirrors of
whatever the instance currently has.

### D6: Org-declared protection via `.git/info/attributes`, never a commit

**Decision**: `panopticon.config.json` gains `protected_paths` — an org-maintained array of
arbitrary paths (skills, tooling modules, future plugin content) customized at the instance level.
`sync-from-template.yml` gains a step, run before `git merge`, that writes each path (with
`merge=ours`) into `.git/info/attributes` — never the tracked `.gitattributes`. This file lives
entirely inside `.git/`, is part of git's attribute stack, is never tracked, never shows in
`git status`, and needs no commit.

This was verified empirically, not assumed:

- An **uncommitted edit to the tracked `.gitattributes`** (the naive "protect it via a
  self-referential `merge=ours` line, don't commit it" approach) works only when the incoming
  merge happens not to touch `.gitattributes` — and **hard-aborts the entire sync** the moment the
  incoming side does touch it (`git merge` refuses outright: *"Your local changes to the following
  files would be overwritten by merge... Aborting"*), staged or unstaged, no exceptions. That
  failure mode is exactly the case that matters (the template adding a new baseline protected-path
  entry), so this approach is unusable, not just imperfect.
- **`.git/info/attributes`, by contrast, has none of this risk**, confirmed across three scenarios:
  routine sync where the incoming commit *also* modifies the tracked `.gitattributes` (protection
  holds, tracked `.gitattributes` merges completely normally with zero special handling needed for
  it at all); first-sync (`--allow-unrelated-histories -X theirs`); and first-sync with a genuine
  same-path conflict (org-customized skill content vs. the template's own default at that exact
  path) — the org's version won even though `-X theirs` would otherwise hand it to the template.

Because this protection is deliberately invisible in the tracked tree, the regeneration step prints
which paths it protected this run to `$GITHUB_STEP_SUMMARY` — the audit trail lives in the
step-summary history plus `panopticon.config.json`'s own (committed, versioned) history of
`protected_paths`, not in a diffable `.gitattributes`.

*Alternative considered*: commit the regenerated `.gitattributes` as its own step before merging
(ordinary tracked-file protection, `.gitattributes` merges normally like any other file).
Rejected per explicit direction ("I'd rather not commit it") once `.git/info/attributes` was
confirmed to achieve the identical protection guarantee with strictly fewer moving parts (no commit
choreography, no risk of the merge aborting, no extra commits cluttering instance-repo history).

### D7: `protected_paths` entries are literal paths for v1, not globs

**Decision (tentative — see Open Questions)**: `protected_paths` lists exact file paths, matching
`PROTECTED_CONFIG_FILES`'s style, not directory globs. An org customizing a skill's `references/`
or `assets/` subdirectory, not just its `SKILL.md`, would need to list each customized file
individually.

*Alternative considered*: glob/prefix support (`".agents/skills/panopticon-doc-generation/**"`).
Deferred — adds real complexity (glob-to-`.gitattributes`-pattern translation, and `.gitattributes`
patterns already support directory prefixes natively via trailing-slash conventions, so this may be
closer to "just document how to write the pattern" than "build glob matching") for a need not yet
confirmed. Flagged as an open question rather than decided outright.

## Risks / Trade-offs

- **[Risk]** `.git/info/attributes` is per-checkout: the regeneration step and `git merge` must run
  in the same job, same working directory. → **Mitigation**: already true — `sync-from-template.yml`
  is a single job; no cross-job or cross-workflow boundary exists for this state to cross.
- **[Risk]** Skills-location detection in CI (`_detect_existing_location()`) could be ambiguous if a
  child repo has populated skill directories in more than one candidate location (e.g. leftover
  from switching agent tools). → **Mitigation**: reuses the exact same heuristic `install.py`
  already relies on for idempotent re-runs (first match in a fixed order) — not a new failure mode,
  just inherited, consistent behavior.
- **[Risk]** `protected_paths` doesn't detect when a declared path *never* diverges from the
  template (a stale declaration protecting nothing) or warn when the template's field-diff-style
  drift accumulates under a protected path. → **Mitigation**: out of scope for v1, consistent with
  keeping this change tightly scoped; a future enhancement parallel to `PROTECTED_CONFIG_FILES`'s
  field-diff warning, not required now.
- **[Trade-off]** CI-mode and local-mode drift detection are two independent implementations (D2) —
  accepted duplication, not something to unify later without revisiting the "no instance clone
  locally" constraint that forces the split.
- **[Risk]** Advisory-only, forever, means real drift can go unnoticed indefinitely if maintainers
  ignore the warning. → No mitigation needed: this is the explicit, deliberate design (D3), not an
  oversight.

## Migration Plan

1. Ship the `tooling-currency` PR checks (ref alignment, skills/tooling diff) — purely additive,
   safe immediately, no staged advisory→blocking rollout needed since this check is never gated
   (unlike `diagram-missing`, which needed a rollout precisely because it eventually becomes
   blocking-capable).
2. Ship `panopticon/sync.py` and its `LOCAL_TOOLING_MODULES` entry — an already-initialized repo
   only gets the new script the next time someone re-runs `install.py` (which vendors the updated
   module list) or otherwise pulls it manually; after that one bootstrap, `python3 -m panopticon.sync`
   keeps itself current going forward, same as every other vendored module already does.
3. Ship `protected_paths` and the `.git/info/attributes` regeneration step in
   `sync-from-template.yml` last — safe to enable immediately; an org with no `protected_paths`
   declared gets a no-op regeneration step and zero behavior change from what `architecture-diagrams`
   already built.
4. Rollback: each piece independently revertable (one workflow step each, one config field, one new
   script) — no schema version bump, no data migration, no interaction with the index or compiled
   index.

## Open Questions

- Final name for the local sync script (`panopticon/sync.py` proposed here; settle in tasks.md
  against any naming collision with existing modules or skill/tooling terminology already in use).
- Does `protected_paths` need glob/prefix support for v1, or are literal per-file paths sufficient
  to start (D7)? Leaning literal-only for v1 given no confirmed immediate need for directory-level
  customization, but not fully settled.
- Should `skills_location` become a persisted field in `panopticon/config.json` (mirroring
  `docs_location`) for extra robustness, instead of relying on runtime detection
  (`_detect_existing_location()`) in both the CI check and the local sync script? D2 defers this —
  worth revisiting if the detection heuristic ever proves ambiguous in practice.
