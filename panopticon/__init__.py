"""Panopticon core tooling: interface indexing, merge/simulation, parsers, CI agent runtime.

Stdlib-only by design — see .agents/skills/panopticon-python-tooling. CI-only modules (llm.py,
drift.py, currency.py, merge.py, extraction.py, skills.py, bootstrap.py, parsers/) are invoked
checkout-and-run (``python3 -m panopticon.<module>``) from an instance-repo checkout; there is no
build step and no third-party dependency. The local-tooling subset used by Phase 2/3 of child-repo
initialization (__init__.py, config.py, docs.py, index.py, init_repo.py — see
panopticon.bootstrap.LOCAL_TOOLING_MODULES) is instead vendored directly into each child repo by
the bootstrap script, so `python3 -m panopticon.docs` / `python3 -m panopticon.init_repo` work
there with no instance-repo checkout needed.
"""

SCHEMA_VERSION = 1
