"""Deterministic interface-name canonicalization: hints first, then normalization rules.

Canonical names are fixed when entries are produced or merged (design D9). The precedence is:

1. **Hints** — ``panopticon-``-prefixed comments in the source/config files that reference the
   interface, e.g. ``# panopticon-interface order-events``. Hints persist naming judgments (made
   by the local agent, possibly with LLM help) so repeated runs are deterministic.
2. **Normalization rules** — pure-function cleanup of the raw name.
3. **LLM judgment** — local agent harness only, guided by the panopticon-interface-naming skill.
   Never in CI: a CI evaluation that cannot resolve a name from hints and rules fails with an
   instruction to add a hint (``UnresolvableNameError``).
"""

import re

HINT_RE = re.compile(r"panopticon-(?P<hint>[a-z][a-z0-9-]*)[ \t:=]+(?P<value>[^\s'\"`]+)")
INTERFACE_HINT = "interface"
# dependency-indexing capability: pins a candidate's canonical name (mirrors INTERFACE_HINT).
DEPENDENCY_HINT = "dependency"
# dependency-indexing capability: links a dependency entry to an existing interface entry
# (`# panopticon-dependency-of <interface-name>`) — set only by an explicit hint, never inferred.
DEPENDENCY_OF_HINT = "dependency-of"

_NORMALIZE_SEPARATORS = re.compile(r"[\s_./:]+")
_DASH_RUNS = re.compile(r"-{2,}")


class UnresolvableNameError(Exception):
    """A canonical name could not be resolved from hints and normalization rules (CI failure)."""

    def __init__(self, raw_name, source_files, hint_name=INTERFACE_HINT):
        self.raw_name = raw_name
        self.source_files = list(source_files)
        files = ", ".join(self.source_files) or "the files referencing the interface"
        super().__init__(
            f"cannot resolve a canonical name for {raw_name!r} from hints or normalization rules. "
            f"Add a hint comment next to the declaration in {files}, e.g. "
            f"'# panopticon-{hint_name} <canonical-name>', and commit it."
        )


def parse_hints(text):
    """All ``panopticon-<hint> <value>`` comments in a text, as (hint, value, line_number)."""
    hints = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in HINT_RE.finditer(line):
            hints.append((match.group("hint"), match.group("value"), line_number))
    return hints


def interface_hints(text):
    """Values of ``panopticon-interface`` hints in file order."""
    return [value for hint, value, _ in parse_hints(text) if hint == INTERFACE_HINT]


def dependency_hints(text):
    """Values of ``panopticon-dependency`` hints in file order (pins a dependency's canonical name)."""
    return [value for hint, value, _ in parse_hints(text) if hint == DEPENDENCY_HINT]


def dependency_of_hints(text):
    """Values of ``panopticon-dependency-of`` hints in file order (interface names to link to)."""
    return [value for hint, value, _ in parse_hints(text) if hint == DEPENDENCY_OF_HINT]


def normalize_name(raw):
    """Deterministic normalization: lowercase; separators to dashes; collapse and trim dashes."""
    name = _NORMALIZE_SEPARATORS.sub("-", str(raw).strip().lower())
    return _DASH_RUNS.sub("-", name).strip("-")


def resolve_name(raw, hint=None, source_files=()):
    """Canonicalize a raw interface name. A hint wins outright; otherwise normalization rules.

    Raises UnresolvableNameError when neither produces a usable name — callers in CI let this
    fail the check; the local agent harness responds by judging a name and writing the hint.
    """
    if hint:
        return normalize_name(hint) or hint
    name = normalize_name(raw)
    if not name:
        raise UnresolvableNameError(raw, source_files)
    return name


def resolve_dependency_name(raw, hint=None, source_files=()):
    """Canonicalize a raw dependency name. A hint wins outright; otherwise the raw name is used
    verbatim (trimmed only) — deliberately **not** run through ``normalize_name``.

    Unlike interface names (human-chosen, benefit from lowercase/dash canonicalization), a
    dependency's raw name is already a canonical machine identifier — a Go module path, a Maven
    ``groupId:artifactId``, a PyPI/npm package name — and normalizing it (lowercasing, collapsing
    separators to dashes) would break exact matching against real import paths and registry
    coordinates. See dependency-indexing capability, "Dependency index schema."

    Raises UnresolvableNameError (instructing a ``panopticon-dependency`` hint) when neither a hint
    nor a usable raw name is available.
    """
    if hint:
        return str(hint).strip()
    name = str(raw).strip()
    if not name:
        raise UnresolvableNameError(raw, source_files, hint_name=DEPENDENCY_HINT)
    return name


def nearest_hint(text, line_number, max_distance=2, hint_type=INTERFACE_HINT):
    """The nearest ``panopticon-<hint_type>`` hint on or within ``max_distance`` lines above the
    given line (defaults to ``panopticon-interface``; pass ``DEPENDENCY_HINT``/``DEPENDENCY_OF_HINT``
    for the dependency-indexing capability's hint forms — same comment-adjacent precedence).

    Lets a hint comment pin the name of the declaration immediately below it without claiming the
    whole file.
    """
    best = None
    for hint, value, hint_line in parse_hints(text):
        if hint != hint_type:
            continue
        if 0 <= line_number - hint_line <= max_distance:
            if best is None or hint_line > best[0]:
                best = (hint_line, value)
    return best[1] if best else None
