"""Starter Go dependency parser: ``go.mod`` module paths, zero-configuration internal detection.

Scope (deliberately narrow — grow via upstream contributions):

- a Go module path embeds the org's own GitHub identity (``github.com/{org}/...``), so an internal
  dependency resolves deterministically from the repo's own ``module`` directive and its ``require``
  block — no ``internal_registries`` config, no network lookup (dependency-indexing capability,
  "Structural zero-configuration detection"). The org identity is read from the repo's own
  ``panopticon/config.json`` (``instance``'s org segment), a local file already present in the repo
  being scanned — not a network call, not org-specific code.
- self-registration: when the repo's own module path is under the org's identity, it self-registers
  as that module's producer (dependency-indexing capability, "Self-registration") — no further
  evidence required for Go, which has no separate publish step.
- two-phase extraction (dependency-indexing capability, "Two-phase extraction"): phase 1 scans
  ``go.mod`` for candidate internal dependencies; phase 2 walks ``.go`` files' import blocks for the
  specific subpackage import paths consumed from each resolved internal dependency, populating
  ``apis`` at import-level granularity.
"""

import re
from pathlib import Path

DEPENDENCY_ECOSYSTEM = "go"

_MODULE_RE = re.compile(r"^module\s+(\S+)", re.MULTILINE)
_REQUIRE_BLOCK_RE = re.compile(r"require\s*\(\s*(.*?)\)", re.DOTALL)
_REQUIRE_LINE_RE = re.compile(r"^require\s+(\S+)\s+(\S+)\s*$", re.MULTILINE)
_REQUIRE_ENTRY_RE = re.compile(r"^\s*(\S+)\s+(\S+)(?:\s*//.*)?$")

_GO_IMPORT_BLOCK_RE = re.compile(r"import\s*\(\s*(.*?)\)", re.DOTALL)
_GO_IMPORT_SINGLE_RE = re.compile(r'^\s*import\s+(?:[A-Za-z_][A-Za-z0-9_]*\s+)?"([^"]+)"', re.MULTILINE)
_GO_IMPORT_ENTRY_RE = re.compile(r'^\s*(?:[A-Za-z_][A-Za-z0-9_]*\s+)?"([^"]+)"\s*(?://.*)?$')


def detect(repo_root):
    return (Path(repo_root) / "go.mod").is_file()


def _org_identity(repo_root):
    """The org's GitHub organization, read from the repo's own ``panopticon/config.json``.

    Returns ``None`` when the repo isn't Panopticon-initialized or has no ``instance`` recorded —
    callers treat that as "structural detection unavailable," not an error.
    """
    from ..config import load_repo_config

    repo_config = load_repo_config(repo_root)
    if not repo_config or not repo_config.get("instance"):
        return None
    return repo_config["instance"].split("/", 1)[0]


def _parse_module_path(text):
    match = _MODULE_RE.search(text)
    return match.group(1) if match else None


def _parse_requires(text):
    """``{module_path: version}`` for every ``require`` entry, block or single-line form."""
    requires = {}
    for block_match in _REQUIRE_BLOCK_RE.finditer(text):
        for line in block_match.group(1).splitlines():
            entry_match = _REQUIRE_ENTRY_RE.match(line)
            if entry_match:
                requires[entry_match.group(1)] = entry_match.group(2)
    for line_match in _REQUIRE_LINE_RE.finditer(text):
        requires[line_match.group(1)] = line_match.group(2)
    return requires


def _internal_prefixes(module_path, requires, org):
    """Module paths (own + required) that are internal, i.e. under ``github.com/{org}/``."""
    prefix = f"github.com/{org}/"
    internal = set()
    if module_path and module_path.startswith(prefix):
        internal.add(module_path)
    for path in requires:
        if path.startswith(prefix):
            internal.add(path)
    return internal


def _go_files(repo_root):
    from . import iter_files

    return iter_files(repo_root, suffixes={".go"})


def _parse_imports(text):
    imports = []
    for block_match in _GO_IMPORT_BLOCK_RE.finditer(text):
        for line in block_match.group(1).splitlines():
            entry_match = _GO_IMPORT_ENTRY_RE.match(line)
            if entry_match:
                imports.append(entry_match.group(1))
    for line_match in _GO_IMPORT_SINGLE_RE.finditer(text):
        imports.append(line_match.group(1))
    return imports


def _owning_module(import_path, internal_prefixes):
    """The internal module path an import belongs to, or ``None`` if it isn't internal."""
    for module_path in internal_prefixes:
        if import_path == module_path or import_path.startswith(module_path + "/"):
            return module_path
    return None


def _candidate(name, hint, role, owned, source_file, apis=None, links_to_interface_hint=None):
    return {
        "raw_name": name,
        "hint": hint,
        "ecosystem": DEPENDENCY_ECOSYSTEM,
        "role": role,
        "source_file": source_file,
        "owned": owned,
        "component": None,
        "apis": apis,
        "links_to_interface_hint": links_to_interface_hint,
    }


def extract(repo_root):
    from . import relative_posix
    from ..naming import DEPENDENCY_HINT, DEPENDENCY_OF_HINT, nearest_hint

    repo_root = Path(repo_root)
    go_mod_path = repo_root / "go.mod"
    if not go_mod_path.is_file():
        return []
    text = go_mod_path.read_text(encoding="utf-8", errors="replace")
    module_path = _parse_module_path(text)
    requires = _parse_requires(text)
    org = _org_identity(repo_root)
    if org is None:
        return []
    internal_prefixes = _internal_prefixes(module_path, requires, org)
    source_file = relative_posix(go_mod_path, repo_root)

    candidates = []
    if module_path and module_path in internal_prefixes:
        line_number = next(
            (i for i, line in enumerate(text.splitlines(), start=1) if line.strip().startswith("module ")),
            1,
        )
        candidates.append(
            _candidate(
                module_path,
                nearest_hint(text, line_number, hint_type=DEPENDENCY_HINT),
                "producer",
                True,
                source_file,
                links_to_interface_hint=nearest_hint(text, line_number, hint_type=DEPENDENCY_OF_HINT),
            )
        )
    for path in requires:
        if path == module_path or path not in internal_prefixes:
            continue
        line_number = next(
            (i for i, line in enumerate(text.splitlines(), start=1) if path in line), 1
        )
        candidates.append(
            _candidate(
                path,
                nearest_hint(text, line_number, hint_type=DEPENDENCY_HINT),
                "consumer",
                False,
                source_file,
                links_to_interface_hint=nearest_hint(text, line_number, hint_type=DEPENDENCY_OF_HINT),
            )
        )

    consumer_prefixes = {p for p in internal_prefixes if p != module_path}
    if consumer_prefixes:
        for go_path in _go_files(repo_root):
            go_text = go_path.read_text(encoding="utf-8", errors="replace")
            go_source_file = relative_posix(go_path, repo_root)
            apis_by_module = {}
            for import_path in _parse_imports(go_text):
                owner = _owning_module(import_path, consumer_prefixes)
                if owner:
                    apis_by_module.setdefault(owner, set()).add(import_path)
            for module_path_key, apis in apis_by_module.items():
                candidates.append(
                    _candidate(
                        module_path_key,
                        None,
                        "consumer",
                        False,
                        go_source_file,
                        apis=sorted(apis),
                    )
                )
    return candidates
