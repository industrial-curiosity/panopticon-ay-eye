"""Deterministic parser registry.

Each parser is a self-contained stdlib-only module (upstreamable to the template repo) exposing:

- ``INTERFACE_TYPE`` — the index ``type`` it emits (registry key)
- ``detect(repo_root) -> bool`` — cheap check that the repo contains material for this parser
- ``extract(repo_root) -> list[candidate]`` — candidate interface entries

Candidates are not index entries yet; the extraction driver (``panopticon.extraction``) resolves
canonical names (hints first) and folds candidates into an index document. Candidate shape::

    {
      "raw_name": "Orders API",       # name as found in the source
      "hint": "orders-api" or None,   # panopticon-interface hint found next to the declaration
      "type": "rest",
      "role": "producer" or "consumer",
      "source_file": "api/openapi.json",   # repo-root-relative, posix separators
      "owned": True,                  # repo declares/creates the interface (owner candidate)
      "component": "api" or None,     # owning component when the parser can tell
    }

Parsers MUST NOT import org-specific code or add dependencies beyond the core tooling's.
"""

from pathlib import Path

from . import kafka_topics, rest_openapi

REGISTRY = {module.INTERFACE_TYPE: module for module in (rest_openapi, kafka_topics)}

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
}


def iter_files(repo_root, suffixes=None):
    """Repo files (pruned of vendored/generated directories), sorted for determinism."""
    repo_root = Path(repo_root)
    results = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(repo_root).parts):
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        results.append(path)
    return sorted(results)


def relative_posix(path, repo_root):
    return Path(path).relative_to(repo_root).as_posix()


def detecting_parsers(repo_root):
    """Registered parsers whose ``detect`` fires for this repo, in registry order."""
    return {
        interface_type: module
        for interface_type, module in sorted(REGISTRY.items())
        if module.detect(repo_root)
    }


def run_parsers(repo_root):
    """Run every detecting parser; returns ``{interface_type: [candidates]}``."""
    return {
        interface_type: module.extract(repo_root)
        for interface_type, module in detecting_parsers(repo_root).items()
    }
