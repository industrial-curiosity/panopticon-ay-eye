# 2026 07 12 Bootstrap Gitignore Pycache Design

## Context

`download_local_tooling()` in `panopticon/bootstrap.py` vendors
`LOCAL_TOOLING_MODULES` into the
child repo's `panopticon/` directory on every bootstrap run (first-time and
idempotent re-run
alike), overwriting in place — the same trust model `download_skills()` and
`download_getting_started_guide()` already use. Skills tell the user's agent to
run those vendored
modules directly (`python3 -m panopticon.docs`, `python3 -m
panopticon.init_repo`), which creates
`panopticon/__pycache__/`. Nothing currently ensures that directory is excluded
from `git add -A`
(the exact command `agent_prompts()` tells the user to run after
initialization).

## Goals / Non-Goals

## Goals

- Guarantee `panopticon/__pycache__/` is gitignored in every bootstrapped child
  repo, independent
  of whatever the child repo's own root `.gitignore` does or doesn't cover.
- Keep the fix idempotent and consistent with bootstrap's existing
  overwrite-in-place model.

## Non-Goals

- Not managing the child repo's root `.gitignore` at all — no appending, no
  merging, no parsing an
  existing file the user may have customized.
- Not addressing bytecode caches from any Python code the child repo has outside
  `panopticon/`
  (that's the child repo's own concern, unrelated to what bootstrap vendors).

## Decisions

- **Write a dedicated `panopticon/.gitignore` (containing `__pycache__/`), not
  touch the root
  `.gitignore`.** A `.gitignore` file scoped to the vendored directory only
  affects paths under
  `panopticon/`, is fully owned by bootstrap (like every other vendored file),
  and requires no
  read-modify-write merge logic against a file the user might have hand-edited.
  Editing the root
  `.gitignore` would need idempotent line-presence checking (don't duplicate
  `__pycache__/` if the
  user already has it, possibly in a different form like `**/__pycache__/`) for
  a benefit — a
  single shared ignore rule — this narrower approach gets without any of that
  complexity.
- **Write unconditionally on every run, not conditionally on first bootstrap.**
  Matches
  `download_local_tooling()`'s own behavior: simpler, self-healing if a user
  ever deletes the file,
  and consistent with the project's stated trust model (git review is the safety
  net for
  vendored-file overwrites, not conditional writes).

## Risks / Trade-offs

- **A child repo with its own unrelated `panopticon/.gitignore` (unlikely, since
  `panopticon/` is a
  vendored directory name) would have it overwritten.** [Risk] → Mitigation:
  `panopticon/` is
  already a directory bootstrap fully owns and overwrites the contents of (per
  `download_local_tooling`'s existing "overwrites in place" behavior) — this is
  consistent with,
  not a new departure from, that existing model.
