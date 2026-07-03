"""Starter Kafka parser: topic configuration files.

Scope (deliberately narrow — grow via upstream contributions). Files whose name contains
``kafka`` or ``topic`` with these shapes:

- ``*.properties`` — ``topic=<name>``, ``*.topic=<name>``, ``topics=<a>,<b>`` lines. Property
  references configure a client, so candidates are ``consumer`` and not owned.
- ``*.json`` — a top-level ``topics`` array. Objects carrying creation settings
  (``partitions``/``replication_factor``/``replication-factor``) declare the topic: ``producer``
  and owned. Plain-string entries or objects without creation settings are references:
  ``consumer``.
- ``*.yaml|yml`` — line-wise scrape of the same two shapes: ``topic: <name>`` references and
  ``topics:`` list items (items with ``partitions`` are creation configs).

A ``panopticon-interface`` hint on or up to two lines above a declaration pins its name
(JSON files, which cannot carry comments, use a file-level hint from a sibling ``.properties`` or
YAML file only via the normal hint precedence at merge time).
"""

import json
import re
from pathlib import Path

INTERFACE_TYPE = "kafka"

_FILE_NAME_RE = re.compile(r"(kafka|topic)", re.IGNORECASE)
_SUFFIXES = {".properties", ".json", ".yaml", ".yml"}
_PROPERTY_RE = re.compile(r"^\s*(?P<key>[A-Za-z0-9_.-]*topics?)\s*[=:]\s*(?P<value>\S+)\s*$")
_YAML_TOPIC_RE = re.compile(r"^\s*topic:\s*(?P<value>[^\s#]+)")
_YAML_LIST_NAME_RE = re.compile(r"^\s*-\s+(name:\s*)?(?P<value>[^\s#:]+)\s*$")
_CREATION_KEYS = ("partitions", "replication_factor", "replication-factor")


def _config_files(repo_root):
    from . import iter_files

    return [
        path
        for path in iter_files(repo_root, suffixes=_SUFFIXES)
        if _FILE_NAME_RE.search(path.name)
    ]


def detect(repo_root):
    return bool(_config_files(repo_root))


def _candidate(name, hint, role, owned, source_file):
    return {
        "raw_name": name,
        "hint": hint,
        "type": INTERFACE_TYPE,
        "role": role,
        "source_file": source_file,
        "owned": owned,
        "component": None,
    }


def _from_properties(text, source_file):
    from ..naming import nearest_hint

    candidates = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = _PROPERTY_RE.match(line.split("#", 1)[0])
        if not match:
            continue
        hint = nearest_hint(text, line_number)
        for name in match.group("value").split(","):
            if name:
                candidates.append(_candidate(name, hint, "consumer", False, source_file))
    return candidates


def _from_json(text, source_file):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return []
    topics = doc.get("topics") if isinstance(doc, dict) else None
    if not isinstance(topics, list):
        return []
    candidates = []
    for topic in topics:
        if isinstance(topic, str):
            candidates.append(_candidate(topic, None, "consumer", False, source_file))
        elif isinstance(topic, dict) and isinstance(topic.get("name"), str):
            creates = any(key in topic for key in _CREATION_KEYS)
            role = "producer" if creates else "consumer"
            candidates.append(_candidate(topic["name"], None, role, creates, source_file))
    return candidates


def _from_yaml(text, source_file):
    from ..naming import nearest_hint

    candidates = []
    lines = text.splitlines()
    in_topics_list = False
    topics_indent = 0
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if stripped == "topics:":
            in_topics_list, topics_indent = True, indent
            continue
        if in_topics_list and indent <= topics_indent and not stripped.startswith("-"):
            in_topics_list = False
        match = _YAML_TOPIC_RE.match(line)
        if match:
            hint = nearest_hint(text, line_number)
            candidates.append(_candidate(match.group("value").strip("'\""), hint, "consumer", False, source_file))
            continue
        if in_topics_list:
            match = _YAML_LIST_NAME_RE.match(line)
            if match:
                block = "\n".join(lines[line_number : line_number + 4])
                creates = any(f"{key}:" in block for key in _CREATION_KEYS)
                hint = nearest_hint(text, line_number)
                role = "producer" if creates else "consumer"
                candidates.append(
                    _candidate(match.group("value").strip("'\""), hint, role, creates, source_file)
                )
    return candidates


def extract(repo_root):
    from . import relative_posix

    repo_root = Path(repo_root)
    candidates = []
    for path in _config_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="replace")
        source_file = relative_posix(path, repo_root)
        if path.suffix == ".properties":
            candidates.extend(_from_properties(text, source_file))
        elif path.suffix == ".json":
            candidates.extend(_from_json(text, source_file))
        else:
            candidates.extend(_from_yaml(text, source_file))
    return candidates
