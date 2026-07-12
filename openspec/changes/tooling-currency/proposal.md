## Why

A child repo's wired workflow ref, its downloaded `panopticon-*` skills, and its vendored local
tooling (`panopticon/{__init__,config,docs,index,init_repo}.py`) are all snapshots taken at
bootstrap time (`install.py`). Nothing currently notices when they drift from what the instance
repo now ships — `docs/planned-work.md` already names this gap ("workflows should check that
skills and workflows are up to date with the instance repo"). A repo can silently run stale
doc-generation rules, a stale index schema understanding, or a workflow pointer nobody remembers
pinning, with no signal short of a maintainer manually re-running `install.py` and diffing by eye.
Separately, an org may customize a `panopticon-*` skill or tooling module at the **instance** repo
level (and, in the future, ship plugin content) — that customization needs to survive
`sync-from-template`'s pull from the upstream template, extending the protected-config mechanism
built for `panopticon.diagram.config.json` to arbitrary, org-declared paths.

## What Changes

- A new deterministic, advisory-only PR check (`panopticon-pr.yml`) warns when a child repo's
  wired `panopticon-pr.yml` `uses:@ref` no longer resolves to the instance repo's current
  default-branch tip commit, and separately when the child's downloaded skills or vendored local
  tooling differ in content from the instance repo's current copies. Both comparisons run against
  the instance repo already checked out by that workflow — no GitHub API calls, no tag
  enumeration, no timestamp comparisons (CI checkout mtimes don't reflect commit history and would
  be actively misleading as a staleness signal). This check never fails the workflow: it is
  explicitly left to "the child repo maintainer's discretion," and is not wired into the existing
  `CHECK_TYPES`/gating mechanism.
- A new local script, vendored alongside the existing local-tooling subset so it's available
  immediately in any already-bootstrapped child repo, lets a developer pull the instance's current
  skills and tooling on demand. Default behavior overwrites unconditionally (git review is the
  safety net, same trust model as `install.py`'s existing idempotent overwrite of vendored
  tooling); `--check-updates` makes it a pure dry run — reports what would change using the same
  git-blob-hash comparison GitHub's API already exposes, writes nothing.
- Every child repo's bootstrap run downloads a new, static, template-authored `PANOPTICON.md` getting
  -started guide to the repo root (concise: repo roles/lifecycle, where architecture diagrams live, and
  the sync commands) — vendored and overwritten idempotently the same way skills/tooling already are. The
  bootstrap script's printed output explicitly names both `PANOPTICON.md` and the literal
  `python3 -m panopticon.sync` command on every run (first bootstrap and re-run alike), so a maintainer
  discovers the sync workflow from the terminal without first knowing the guide exists.
- Each child repo's `## Architecture diagram` section's back-link to the instance repo's org-wide diagram
  is fixed. Every child repo's docs are merged into the instance repo at `docs/{repo}/` (master-sync
  capability), so the org diagram and every repo's own diagram section end up in the *same* tree — the
  back-link is therefore a plain relative link (`../architecture.md#{repo}`), not an absolute GitHub URL,
  and resolves correctly once merged (not before, by design — see design.md D9). The previous prose was
  a bare, malformed URL missing GitHub's required `/blob/<branch>/` segment (a live 404 as written); no
  new config field or branch resolution is needed for the fix itself. The already-relative same-repo
  diagram links (`panopticon/diagrams.py`'s `docs/{other}/architecture.md`) were already correct and
  are unchanged.
- The child repo config (`panopticon/config.json`) gains a new `instance_default_branch` field —
  resolved via the same GitHub token/transport mechanism the bootstrap script already uses for every
  other request (never `gh api` as a subprocess, which depends on the separate, narrower precondition
  of `gh auth login`; never guessed; never derived from the possibly-pinned-tag `workflow_ref`; design
  D10/D11 — a different need from the diagram-link fix above, not a reintroduction of it). It powers a
  new local script, `python3 -m panopticon.org_diagram_link`, vendored alongside `sync.py`, that a
  developer runs from their child repo checkout — before any merge — to print an immediately
  clickable, fully-resolved link to this repo's section of the org diagram
  (`{instance-repo-url}/blob/{instance_default_branch}/docs/architecture.md#{repo}`). Config is always
  checked first (no network call in the common case); the script falls back to a live `gh` lookup only
  when the field is genuinely absent, and fails loudly (never guessing) if that also fails. The
  bootstrap script also now refreshes this field in place on every rerun of an already-initialized
  repo (design D11) — a narrow exception to its general "never write panopticon/config.json" rule,
  scoped to updating one field of an already-existing file, never creating it.
- `panopticon.config.json` gains a new org-declared `protected_paths` field — arbitrary paths
  (skills, tooling modules, future plugin content) an org has customized at the instance level.
  `sync-from-template.yml` gains a step, run before `git merge`, that writes these paths (each with
  the `merge=ours` attribute) into `.git/info/attributes` — never the tracked `.gitattributes`,
  never committed — so this protection can never abort a merge the way an uncommitted change to a
  *tracked* file the incoming side also touches does (verified empirically; see design.md). The
  tracked `.gitattributes` is untouched by this change and keeps carrying only the
  template-declared baseline (`PROTECTED_CONFIG_FILES`) exactly as already built. Because the
  protected-path list is no longer visible in the tracked tree, the workflow step prints which
  paths it protected this run to the GitHub Actions step summary.

## Capabilities

### New Capabilities

- `tooling-currency`: owns what "in sync with the instance repo" means for a child repo's wired
  workflow ref, downloaded skills, and vendored local tooling — the comparison semantics (content,
  never timestamps), the always-advisory nature of the CI check, and the local sync script's
  default-overwrite / `--check-updates`-is-dry-run-only contract — that `pr-evaluation` and
  `repo-initialization` each hook into, mirroring how `architecture-diagrams` owns diagram content
  contracts that other capabilities consume.

### Modified Capabilities

- `repo-initialization`: `sync-from-template.yml`'s protected-config mechanism (design D7 of the
  `architecture-diagrams` change) generalizes from a template-declared, single-entry registry to
  also cover an org-declared, open-ended `protected_paths` list, protected via `.git/info/attributes`
  regenerated every run rather than the tracked `.gitattributes`; the local-tooling vendoring list
  gains the new sync script so it's available in any already-bootstrapped child repo. Bootstrap also
  now vendors a static `PANOPTICON.md` getting-started guide and prints the sync command on every run
  (design D8). The finalization step gains a new `instance_default_branch` config field, resolved
  deterministically via the same token/transport mechanism the bootstrap script already uses, not
  `gh api` as a subprocess (design D10/D11), and the local-tooling vendoring list gains the new
  org-diagram-link script. The bootstrap script also gains a narrow, explicit exception to its "never
  write panopticon/config.json" rule: on rerun of an already-initialized repo, it refreshes just the
  `instance_default_branch` field in place (design D11) — never creating the file, only updating one
  field of an already-existing one.
- `architecture-diagrams`: the child-repo → org-diagram back-link is corrected from a malformed,
  non-resolving bare URL to a proper relative markdown link authored for its post-merge location in
  the instance repo (design D9) — a fix, not a new capability, since the link's *intent* ("navigate to
  the org diagram") was already specified; only the URL's exact shape was under-specified and, as
  implemented, wrong. Separately gains a new "Org-diagram link script" requirement (design D10) — a
  local script that prints a resolvable deep link to the org diagram, complementing the embedded
  back-link for the pre-merge case it structurally can't cover.
- `pr-evaluation`: adds the tooling-currency check's CI wiring (workflow-ref alignment,
  skills/tooling diff) as a new, always-advisory step — distinct from the existing combined report
  and its TL;DR action-collapsing, since remediation here ("run the sync script") doesn't fit that
  report's doc-generation-centric action vocabulary and nothing here is a gate a developer must
  clear before merge.

## Impact

- **Code**: `panopticon/config.py` (`protected_paths` schema), a new `panopticon/sync.py` (or
  equivalent name settled in design) implementing the local sync script, `panopticon/bootstrap.py`
  (`LOCAL_TOOLING_MODULES` gains the new script; new `PANOPTICON.md` download step; printed output
  gains the sync-command reference), a new template-root `PANOPTICON.md` source file authored once and
  downloaded verbatim, `.agents/skills/panopticon-doc-generation/` (`SKILL.md` and
  `assets/architecture-template.md` — corrected org-diagram back-link to a relative link),
  `panopticon/init_repo.py` (finalization resolves and persists `instance_default_branch` via the
  GitHub API), a new `panopticon/org_diagram_link.py` implementing the org-diagram link script, added
  to `LOCAL_TOOLING_MODULES` alongside `sync.py`.
- **Workflows**: `panopticon-pr.yml` (two new advisory-only steps: workflow-ref alignment,
  skills/tooling diff), `sync-from-template.yml` (new `.git/info/attributes` regeneration step with
  step-summary visibility, run before the merge step).
- **Docs**: `docs/setup-guide.md`, `README.md`, `docs/testing.md` — the sync script's usage, the
  CI warning's meaning and remediation, the `protected_paths` config field, `PANOPTICON.md`, and the
  org-diagram link script all need to be documented clearly, per explicit requirement.
- **No breaking changes**: purely additive. No new `CHECK_TYPES`/gating entry (this check is
  deliberately never gated). No changes to the index schema or existing protected-config behavior
  for `panopticon.diagram.config.json`, which keeps working exactly as `architecture-diagrams`
  built it.
