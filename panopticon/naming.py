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

_NORMALIZE_SEPARATORS = re.compile(r"[\s_./:]+")
_DASH_RUNS = re.compile(r"-{2,}")


class UnresolvableNameError(Exception):
    """A canonical name could not be resolved from hints and normalization rules (CI failure)."""

    def __init__(self, raw_name, source_files):
        self.raw_name = raw_name
        self.source_files = list(source_files)
        files = ", ".join(self.source_files) or "the files referencing the interface"
        super().__init__(
            f"cannot resolve a canonical name for {raw_name!r} from hints or normalization rules. "
            f"Add a hint comment next to the declaration in {files}, e.g. "
            f"'# panopticon-interface <canonical-name>', and commit it."
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


def nearest_hint(text, line_number, max_distance=2):
    """The ``panopticon-interface`` hint on or within ``max_distance`` lines above the given line.

    Lets a hint comment pin the name of the declaration immediately below it without claiming the
    whole file.
    """
    best = None
    for hint, value, hint_line in parse_hints(text):
        if hint != INTERFACE_HINT:
            continue
        if 0 <= line_number - hint_line <= max_distance:
            if best is None or hint_line > best[0]:
                best = (hint_line, value)
    return best[1] if best else None
