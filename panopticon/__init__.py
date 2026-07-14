"""Panopticon core tooling: interface/dependency indexing, merge/simulation, parsers, CI agent
runtime.

Stdlib-only by design — see .agents/skills/panopticon-python-tooling. CI-only modules (llm.py,
drift.py, currency.py, merge.py, extraction.py, dependency_extraction.py, dependency_lookup.py,
skills.py, bootstrap.py, tooling_currency.py, parsers/) are invoked checkout-and-run
(``python3 -m panopticon.<module>``) from an instance-repo checkout; there is no build step and no
third-party dependency. The local-tooling subset used by Phase 2/3 of child-repo initialization
and by on-demand syncing (__init__.py, config.py, dependencies.py, docs.py, index.py, init_repo.py,
sync.py, org_diagram_link.py — see panopticon.bootstrap.LOCAL_TOOLING_MODULES) is instead vendored
directly into each child repo by the bootstrap script, so `python3 -m panopticon.docs` /
`python3 -m panopticon.init_repo` / `python3 -m panopticon.sync` /
`python3 -m panopticon.org_diagram_link` work there with no instance-repo checkout needed —
``dependencies.py`` joins this set so the local agent (panopticon-dependency-naming skill) can
validate and save a local ``panopticon/dependencies.json`` the same way ``index.py`` already lets
it save ``panopticon/index.json``.
"""

SCHEMA_VERSION = 1
