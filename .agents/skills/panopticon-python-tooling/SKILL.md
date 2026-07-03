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
