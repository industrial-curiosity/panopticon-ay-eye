# Repo Initialization Spec

## ADDED Requirements

### Requirement: Vendored tooling's bytecode cache is gitignored

Whenever the bootstrap script vendors the local-tooling subset of the
`panopticon` package (see
"Local tooling package vendored into child repo"), it SHALL also write
`panopticon/.gitignore`
containing `__pycache__/`, so that running the vendored modules (`python3 -m
panopticon.docs`,
`python3 -m panopticon.init_repo`, etc.) never leaves compiled bytecode as an
untracked-but-visible
or accidentally-staged artifact in the child repo. This is written
unconditionally on every
bootstrap run, first-time and idempotent re-run alike, using the same
overwrite-in-place trust
model as the vendored modules themselves.

#### Scenario: Fresh bootstrap creates the gitignore alongside vendored modules

- **GIVEN** a child repo that has never run the bootstrap script before
- **WHEN** the bootstrap script vendors the local-tooling package
- **THEN** `panopticon/.gitignore` exists and contains `__pycache__/`

#### Scenario: Bytecode from running vendored modules is not tracked

- **GIVEN** a freshly bootstrapped child repo
- **WHEN** the user's agent runs `python3 -m panopticon.docs` (or any other
  vendored module),
  producing `panopticon/__pycache__/`
- **THEN** `git status` does not list anything under `panopticon/__pycache__/`
  as untracked

#### Scenario: Re-run does not duplicate or remove the entry

- **WHEN** the bootstrap script runs again on an already-bootstrapped repo
- **THEN** `panopticon/.gitignore` still exists, still contains exactly
  `__pycache__/`, and no
  duplicate or additional gitignore files are created
