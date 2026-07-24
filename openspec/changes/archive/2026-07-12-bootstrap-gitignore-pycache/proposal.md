# 2026 07 12 Bootstrap Gitignore Pycache Proposal

## Why

The bootstrap installer vendors Python modules into every child repo's
`panopticon/` directory
(`download_local_tooling`), and the skills it downloads instruct the user's
agent to run those
modules directly (`python3 -m panopticon.docs`, `python3 -m
panopticon.init_repo`, etc.). Running
them creates a `panopticon/__pycache__/` directory of compiled bytecode. Nothing
in the bootstrap
flow currently guarantees that directory is gitignored, so a child repo with no
pre-existing
Python `.gitignore` entry will have compiled bytecode staged on the next `git
add -A` the
getting-started guide tells the user to run — noise in the diff and the repo,
with no benefit.

## What Changes

- Bootstrap writes a dedicated `panopticon/.gitignore` containing `__pycache__/`
  alongside the
  vendored modules, so bytecode from running them is excluded regardless of
  whether the child
  repo's own root `.gitignore` already handles Python.
- Written unconditionally on every bootstrap run (first-time and idempotent
  re-run alike), same
  overwrite-in-place trust model already used for the vendored modules and
  skills.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `repo-initialization`: the bootstrap script gains a new requirement — it SHALL
  write
  `panopticon/.gitignore` (containing `__pycache__/`) whenever it vendors the
  local-tooling
  package, so the child repo never accidentally commits compiled bytecode from
  running the
  vendored modules.

## Impact

- `panopticon/bootstrap.py` — `download_local_tooling()` (or a new function
  called alongside it)
  and `main()`'s vendoring step.
- No effect on already-initialized repos until they next re-run the bootstrap
  script; this isn't a
  breaking change and requires no migration.
