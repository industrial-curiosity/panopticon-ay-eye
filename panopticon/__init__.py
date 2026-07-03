"""Panopticon core tooling: interface indexing, merge/simulation, parsers, CI agent runtime.

Stdlib-only by design — see .agents/skills/panopticon-python-tooling. Tooling is invoked
checkout-and-run (``python3 -m panopticon.<module>``) from an instance-repo checkout; there is no
build step and no third-party dependency.
"""

SCHEMA_VERSION = 1
