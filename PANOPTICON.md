<!-- Downloaded by Panopticon's bootstrap script (install.py) — identical in every child repo of
     this instance. Re-run install.py to update; don't hand-edit, your changes will be overwritten
     on the next bootstrap re-run. -->

# Panopticon — getting started

This repo is a **child repo** in a Panopticon setup. Panopticon keeps this repo's documentation and
interface index current, and merges them into a shared **instance repo** so the whole organization can
see cross-repo architecture and interfaces in one place.

## How it works

- **Template repo** — the shared tooling and workflows every instance starts from.
- **Instance repo** — your org's private knowledge base: every child repo's docs, the compiled
  cross-repo interface index, and org-wide configuration. See `panopticon/config.json`'s `instance`
  field for which repo that is.
- **This repo (a child repo)** — owns its own docs and interface index, kept current by your AI agent
  and verified by CI on every pull request.

On every pull request, Panopticon checks that docs and the interface index are current and simulates
this repo's interface changes against the instance's compiled index, reporting conflicts. On every
merge to this repo's default branch, its docs and index are pushed into the instance repo, and the
org-wide architecture diagram is rebuilt from the fresh compiled index.

## Where to find architecture diagrams

- **This repo's own `README.md`** — links to both diagrams at the top: this repo's own (relative,
  resolves once merged into the instance) and the org diagram (a fully-qualified GitHub URL, clickable
  immediately, kept current by doc generation).
- **This repo's own diagram** — the `## Architecture diagram` section in this repo's own
  `architecture.md`.
- **The org-wide diagram** — `docs/architecture.md` at the instance repo's root, rebuilt on every
  merge from every child repo's current interfaces. This repo's own diagram section links to its
  place in that org-wide picture once this repo's docs have been merged into the instance — that
  link only resolves *after* the merge, not before.

To regenerate an immediately clickable link to the org diagram yourself, before any merge:

```bash
python3 -m panopticon.org_diagram_link
```

This prints a single resolvable URL, reading `panopticon/config.json` first — no network call in
the common case. If that config is missing the branch it needs, it falls back to a live lookup
(using the same `GH_TOKEN`/`GITHUB_TOKEN`/`gh auth token` credentials the rest of this repo's
tooling already uses) before giving up. No instance repo clone either way.

## Keeping this repo's skills and tooling current

The skills and vendored `panopticon/` tooling in this repo are snapshots taken at bootstrap time.
Nothing prompts a refresh automatically — pull the instance's current versions on demand:

```bash
python3 -m panopticon.sync
```

This overwrites this repo's skills and vendored tooling unconditionally from the instance's current
default branch. There's no per-file protection — review `git diff`/`git status` before committing,
and don't commit anything you disagree with.

To see what would change without writing anything:

```bash
python3 -m panopticon.sync --check-updates
```

Every pull request also runs an advisory (never blocking) check that warns when this repo's wired
workflow ref, skills, or vendored tooling have drifted from the instance's current default branch —
acting on that warning is at your discretion.
