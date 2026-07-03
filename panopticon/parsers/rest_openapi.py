"""Starter REST parser: OpenAPI/Swagger specification files.

Scope (deliberately narrow — grow via upstream contributions):

- files named ``openapi*.json|yaml|yml`` or ``swagger*.json|yaml|yml`` anywhere in the repo
- the interface name comes from a ``panopticon-interface`` hint in the file when present,
  otherwise from ``info.title``
- a spec file declares the API this repo serves, so candidates are ``producer`` and ``owned``

YAML is scraped line-wise for ``info.title`` (the stdlib has no YAML parser and a full one is not
justified for one field — see panopticon-python-tooling); JSON is parsed properly.
"""

import json
import re
from pathlib import Path

INTERFACE_TYPE = "rest"

_SPEC_NAME_RE = re.compile(r"^(openapi|swagger)[^/]*\.(json|ya?ml)$", re.IGNORECASE)
_YAML_KEY_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*?)\s*$")


def _spec_files(repo_root):
    from . import iter_files

    return [path for path in iter_files(repo_root) if _SPEC_NAME_RE.match(path.name)]


def detect(repo_root):
    return bool(_spec_files(repo_root))


def _title_from_json(text):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(doc, dict) or not ("openapi" in doc or "swagger" in doc):
        return None
    info = doc.get("info")
    title = info.get("title") if isinstance(info, dict) else None
    return title if isinstance(title, str) and title.strip() else None


def _title_from_yaml(text):
    """Line-wise scrape of ``info: / title:`` — indentation-based, comments ignored."""
    info_indent = None
    for line in text.splitlines():
        stripped = line.split("#", 1)[0]
        match = _YAML_KEY_RE.match(stripped)
        if not match:
            continue
        indent, key, value = len(match.group("indent")), match.group("key"), match.group("value")
        if info_indent is None:
            if key == "info" and not value:
                info_indent = indent
        elif indent <= info_indent:
            info_indent = indent if key == "info" and not value else None
        elif key == "title" and value:
            return value.strip("'\"")
    return None


def extract(repo_root):
    from . import relative_posix
    from ..naming import interface_hints

    repo_root = Path(repo_root)
    candidates = []
    for path in _spec_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".json":
            title = _title_from_json(text)
        else:
            title = _title_from_yaml(text)
        hints = interface_hints(text)
        if title is None and not hints:
            continue
        candidates.append(
            {
                "raw_name": title or hints[0],
                "hint": hints[0] if hints else None,
                "type": INTERFACE_TYPE,
                "role": "producer",
                "source_file": relative_posix(path, repo_root),
                "owned": True,
                "component": None,
            }
        )
    return candidates
