### Requirement: Workflow-ref alignment check

The PR workflow SHALL determine whether a child repo's wired `panopticon-pr.yml` caller workflow
(`uses: <instance>/.github/workflows/panopticon-pr.yml@<ref>`) currently resolves to the same
commit as the instance repo's default branch tip, using the instance repo checkout the PR workflow
already performs — no tag enumeration, no additional checkout configuration. Equal → no warning.
Different, or the ref does not resolve to any commit on the instance repo → the check SHALL emit a
non-blocking `::warning::` naming the wired ref and that it no longer matches the instance's
current default branch.

#### Scenario: Wired ref matches the instance's current default branch tip

- **WHEN** a child repo's caller workflow is wired to a ref that resolves to the same commit as the
  instance repo's current default branch tip
- **THEN** the check emits no warning

#### Scenario: Wired ref resolves to an older commit

- **GIVEN** a child repo's caller workflow is wired to a tag or branch that resolves to a commit
  behind the instance repo's current default branch tip
- **WHEN** the workflow-ref alignment check runs
- **THEN** it emits a non-blocking `::warning::` naming the wired ref, left to the child repo
  maintainer's discretion to act on or ignore

#### Scenario: Wired ref no longer exists

- **GIVEN** a child repo's caller workflow is wired to a tag that has since been deleted from the
  instance repo
- **WHEN** the workflow-ref alignment check runs
- **THEN** it emits a non-blocking `::warning::` stating the wired ref could not be resolved

### Requirement: Skills and tooling drift check

The PR workflow SHALL compare, by content, the child repo's downloaded `panopticon-*` skills and
vendored local-tooling modules against the instance repo's current copies of the same files, using
the instance repo checkout the PR workflow already performs. Comparison SHALL be content-based
(e.g. a direct diff, or a hash comparison) — file modification timestamps SHALL NOT be used as a
staleness signal, since CI checkout timestamps reflect checkout time, not commit history, and would
produce false or missed findings. Any file that differs, is missing from the child, or is missing
from the instance's current copy SHALL be named in a non-blocking `::warning::`.

The child repo's skills location (which of the candidate locations documented in
`docs/agentskills-support.md` the repo's skills live in) SHALL be determined the same way the
bootstrap installer's idempotent re-run already determines it, not by requiring a new persisted
configuration field.

#### Scenario: Skills content matches the instance

- **WHEN** every `panopticon-*` skill file in the child repo has identical content to the instance
  repo's current copy
- **THEN** the check emits no warning for skills

#### Scenario: A vendored tooling module has drifted

- **GIVEN** the child repo's vendored `panopticon/docs.py` differs in content from the instance
  repo's current `panopticon/docs.py`
- **WHEN** the skills and tooling drift check runs
- **THEN** it emits a non-blocking `::warning::` naming `panopticon/docs.py` as out of date

#### Scenario: A skill exists in the instance but not the child

- **GIVEN** the instance repo has a `panopticon-*` skill the child repo has never downloaded
- **WHEN** the skills and tooling drift check runs
- **THEN** it emits a non-blocking `::warning::` naming the missing skill

### Requirement: Tooling-currency checks are always advisory

Neither the workflow-ref alignment check nor the skills and tooling drift check SHALL have an entry
in the org config's check-type/gating mechanism, and neither SHALL ever fail the PR workflow,
regardless of org configuration. Their findings SHALL be reported as plain `::warning::` output
(visible in the GitHub Actions step summary and as inline PR annotations), left entirely to the
child repo maintainer's discretion. They SHALL NOT be included in the PR workflow's combined
TL;DR report, since that report's contract is a list of actions a developer must take before merge,
and nothing a tooling-currency check finds is required before merge.

#### Scenario: Drifted tooling never fails the workflow

- **GIVEN** the skills and tooling drift check finds every vendored module out of date
- **WHEN** the PR workflow's gating step runs
- **THEN** the workflow succeeds regardless — this finding has no bearing on the exit status

#### Scenario: Tooling-currency findings are absent from the combined report

- **GIVEN** the workflow-ref alignment check and the skills/tooling drift check both find drift
- **WHEN** the PR workflow's combined TL;DR report is built
- **THEN** neither finding appears in that report; they are reported separately as their own
  `::warning::` output

### Requirement: Local sync script

The template repo SHALL provide a script, runnable from an already-bootstrapped child repo with no
instance repo clone (`python3 -m panopticon.sync` or equivalent), that fetches the instance repo's
current default-branch copies of the child's downloaded skills and vendored local-tooling modules
and overwrites the child repo's copies unconditionally. The script SHALL NOT protect any file at
the child-repo layer — the user's own review of the resulting `git diff`/`git status` before
committing is the only safety mechanism, matching the trust model the bootstrap installer's existing
idempotent overwrite already uses for vendored tooling.

Given a `--check-updates` flag, the script SHALL run as a pure dry run: it SHALL report which files
would change (using the same content-based comparison the GitHub API already exposes — a git blob
hash comparison, not timestamps) and SHALL NOT write any file.

#### Scenario: Default run overwrites unconditionally

- **WHEN** the sync script is run with no flags in a child repo whose skills or tooling have drifted
  from the instance repo
- **THEN** every drifted file is overwritten in place with the instance repo's current content, with
  no prompt and no protection for any individual file

#### Scenario: --check-updates writes nothing

- **WHEN** the sync script is run with `--check-updates`
- **THEN** it reports which files would change and exits without writing, modifying, or deleting any
  file in the child repo

#### Scenario: Nothing to sync

- **GIVEN** every skill and vendored tooling file in the child repo already matches the instance
  repo's current content
- **WHEN** the sync script runs (with or without `--check-updates`)
- **THEN** it reports that everything is current and makes no changes

### Requirement: Org-declared instance-level customization protection

The instance repo's `panopticon.config.json` SHALL support an org-declared `protected_paths` field
listing paths (skills, vendored tooling modules, or other instance-repo content) the org has
customized at the instance level and which SHALL NOT be overwritten by `sync-from-template`'s pull
from the upstream template. This is distinct from the template-declared protected-config registry
(`panopticon.diagram.config.json` and any future entries the template itself declares): the org
maintains this list itself, and the template has no knowledge of it in advance.

Protection for these org-declared paths SHALL be applied via a mechanism that requires no commit —
writing them, with the `merge=ours` attribute, to a location outside the tracked working tree
(`.git/info/attributes` or equivalent) rather than to the tracked `.gitattributes` file. Protecting
a *tracked* file via an uncommitted change to that same file is explicitly insufficient: when the
incoming template merge also modifies that file, git refuses to proceed with the merge at all
rather than silently ignoring the local uncommitted change — a failure mode this requirement
exists specifically to avoid.

Because this protection is not visible in the tracked tree, the `sync-from-template` workflow run
that applies it SHALL print, to the GitHub Actions step summary, which paths were protected during
that run.

#### Scenario: Org-declared path survives a routine sync

- **GIVEN** the instance repo's `panopticon.config.json` lists a customized skill file in
  `protected_paths`, and the incoming template sync also modifies that same file's default content
- **WHEN** `sync-from-template` runs
- **THEN** the instance's customized version of that file is unchanged after the sync, and the sync
  completes without the merge aborting

#### Scenario: Org-declared path survives a first-time sync

- **GIVEN** an instance repo created via "Use this template" with a `protected_paths` entry for a
  file that also exists in the template with different content (a genuine same-path conflict)
- **WHEN** `sync-from-template` runs its first-time sync (`-X theirs`, no common ancestor)
- **THEN** the instance's version of that file wins, even though `-X theirs` would otherwise hand it
  to the template

#### Scenario: Protected paths are named in the step summary

- **GIVEN** `panopticon.config.json` lists one or more `protected_paths` entries
- **WHEN** `sync-from-template` runs
- **THEN** the GitHub Actions step summary names every path that was protected during that run
