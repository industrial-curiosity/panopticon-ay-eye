---
name: panopticon-python-tooling
description: >-
  Simplicity requirements for Panopticon's Python tooling. Apply when writing
  or editing any Python code in this repo, adding or proposing a dependency,
  or designing how tooling is invoked in CI or locally — even for a small
  script or a single import.
---

# Python tooling simplicity rules

Panopticon tooling runs inside other organizations' CI and on developer
machines during repo initialization. Every requirement we add is friction
multiplied across every child repo of every org, so requirements must be as
simple as possible.

## Rules

- **Stdlib first.** Reach for the standard library before any third-party
  package. `json`, `argparse`, `pathlib`, `urllib`, `subprocess` cover most
  of this project's needs.
- **Justify every dependency.** A third-party package must earn its place:
  state in the PR/design what it provides that the stdlib cannot, and pin it.
  Prefer zero-dependency tooling; treat each addition as a design decision,
  not a convenience.
- **Checkout-and-run invocation.** Tooling must work on a bare CI runner with
  a checkout and a system `python3` — no build step, no compiled extensions,
  no framework bootstrapping. If dependencies exist, a single
  `pip install -r requirements.txt` must be the entire setup.
- **Self-contained parsers.** Each deterministic parser must be independently
  contributable upstream to the template repo: no imports from org-specific
  code, no shared mutable state, dependencies limited to what the core
  tooling already requires.
- **No heavy frameworks.** LLM access goes through the org-configured
  endpoint (litellm-compatible HTTP first); do not add agent frameworks or
  provider SDKs to the Python tooling.
- **Importable logic, thin entry points.** Any script meant to be curl-runnable
  or invoked externally must put all logic in an importable module (e.g.,
  `panopticon/bootstrap.py`). The entry-point file (`install.py`) is a single
  `from module import main; sys.exit(main() or 0)`. This makes the logic
  unit-testable without subprocess invocation.
- **Injectable dependencies for testability.** Functions that call
  `urllib.request.urlopen` must accept it as a keyword parameter with the real
  implementation as the default (e.g., `def fetch(url, urlopen=urllib.request.urlopen)`).
  Tests inject a mock; production callers pass nothing. Never patch at the module
  level when injection is possible.
- **Initialization flag last.** `panopticon/config.json` (and any equivalent
  completion sentinel) must be the absolute last artifact written, only after all
  validation passes. If validation fails, the flag must not exist. Tests that check
  this invariant must confirm the flag is absent on failure and present on success
  in a single test (not two independent tests that can drift).
