"""Interface index documents: schema, load, validate, save.

One JSON schema serves all three index kinds (see the panopticon-index-schema skill):

- **local** index — ``panopticon/index.json`` in a child repo
- **shard** — ``interfaces/{repo}.json`` in the instance repo
- **compiled** index — ``interfaces/index.json`` in the instance repo

Document shape::

    {
      "schema_version": 1,
      "interfaces": {
        "<canonical-name>": [
          {
            "owner": {"repo": "svc-a", "component": "api"},   # or null
            "type": "rest",
            "consumer": [{"repo": "svc-b", "source_files": ["src/client.py"]}],
            "producer": [{"repo": "svc-a", "source_files": ["api/openapi.json"]}],
            "extracted_by": "llm"                              # optional provenance tag
          }
        ]
      },
      "conflicts": []   # compiled index only, recomputed on every rebuild
    }

Repo objects inside a compiled index may also carry ``extracted_by`` so per-repo provenance
survives the shard union. Local indexes and shards mention only their own repo in
``consumer``/``producer`` and never contain ``conflicts`` — a repo only knows what it knows.

Saving is deterministic (sorted keys, sorted lists, fixed indentation) so the compiled-index
rebuild is byte-identical for identical shards.
"""

import json
from pathlib import Path

from . import SCHEMA_VERSION

KIND_LOCAL = "local"
KIND_SHARD = "shard"
KIND_COMPILED = "compiled"

CONFLICT_REASONS = ("ownership-dispute", "owner-attribution-mismatch")


class IndexValidationError(Exception):
    """Raised when an index document does not satisfy the schema."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("invalid index document:\n" + "\n".join(f"- {p}" for p in self.problems))


def empty_index(kind=KIND_LOCAL):
    doc = {"schema_version": SCHEMA_VERSION, "interfaces": {}}
    if kind == KIND_COMPILED:
        doc["conflicts"] = []
    return doc


def _validate_repo_object(obj, where, problems):
    if not isinstance(obj, dict):
        problems.append(f"{where}: repo object must be an object")
        return
    repo = obj.get("repo")
    if not isinstance(repo, str) or not repo:
        problems.append(f"{where}: repo object needs a non-empty 'repo' string")
    files = obj.get("source_files")
    if not isinstance(files, list) or not all(isinstance(f, str) and f for f in files):
        problems.append(f"{where}: 'source_files' must be a list of non-empty strings")
    if "extracted_by" in obj and obj["extracted_by"] != "llm":
        problems.append(f"{where}: 'extracted_by' may only be 'llm'")
    unknown = set(obj) - {"repo", "source_files", "extracted_by"}
    if unknown:
        problems.append(f"{where}: unknown repo-object fields {sorted(unknown)}")


def _validate_owner(owner, where, problems):
    if owner is None:
        return
    if not isinstance(owner, dict):
        problems.append(f"{where}: 'owner' must be null or an object")
        return
    if not isinstance(owner.get("repo"), str) or not owner["repo"]:
        problems.append(f"{where}: owner needs a non-empty 'repo' string")
    if not isinstance(owner.get("component"), str):
        problems.append(f"{where}: owner needs a 'component' string")
    unknown = set(owner) - {"repo", "component"}
    if unknown:
        problems.append(f"{where}: unknown owner fields {sorted(unknown)}")


def _validate_interface_object(entry, where, kind, repo, problems):
    if not isinstance(entry, dict):
        problems.append(f"{where}: interface object must be an object")
        return
    if not isinstance(entry.get("type"), str) or not entry["type"]:
        problems.append(f"{where}: needs a non-empty 'type' string")
    _validate_owner(entry.get("owner"), where, problems)
    empty = True
    for role in ("consumer", "producer"):
        role_list = entry.get(role)
        if not isinstance(role_list, list):
            problems.append(f"{where}: '{role}' must be a list of repo objects")
            continue
        seen = set()
        for i, robj in enumerate(role_list):
            _validate_repo_object(robj, f"{where}.{role}[{i}]", problems)
            if isinstance(robj, dict):
                empty = False
                name = robj.get("repo")
                if name in seen:
                    problems.append(f"{where}: duplicate repo '{name}' in '{role}'")
                seen.add(name)
                if kind in (KIND_LOCAL, KIND_SHARD) and repo and name != repo:
                    problems.append(
                        f"{where}: {kind} index for '{repo}' may only mention itself, found '{name}'"
                    )
    if empty:
        problems.append(f"{where}: both 'consumer' and 'producer' are empty; empty entries must be removed")
    if "extracted_by" in entry and entry["extracted_by"] != "llm":
        problems.append(f"{where}: 'extracted_by' may only be 'llm'")
    unknown = set(entry) - {"owner", "type", "consumer", "producer", "extracted_by"}
    if unknown:
        problems.append(f"{where}: unknown interface-object fields {sorted(unknown)}")


def _validate_conflict(conflict, where, problems):
    if not isinstance(conflict, dict):
        problems.append(f"{where}: conflict entry must be an object")
        return
    for field in ("name", "type", "reason", "details"):
        if not isinstance(conflict.get(field), str) or not conflict[field]:
            problems.append(f"{where}: needs a non-empty '{field}' string")
    if conflict.get("reason") not in CONFLICT_REASONS:
        problems.append(f"{where}: 'reason' must be one of {list(CONFLICT_REASONS)}")
    claims = conflict.get("claims")
    if not isinstance(claims, list) or not claims:
        problems.append(f"{where}: 'claims' must be a non-empty list")
    else:
        for i, claim in enumerate(claims):
            if not isinstance(claim, dict) or not isinstance(claim.get("claimed_by"), str):
                problems.append(f"{where}.claims[{i}]: needs a 'claimed_by' repo string")
            else:
                _validate_owner(claim.get("owner"), f"{where}.claims[{i}]", problems)
    unknown = set(conflict) - {"name", "type", "reason", "details", "claims"}
    if unknown:
        problems.append(f"{where}: unknown conflict fields {sorted(unknown)}")


def validate_index(doc, kind=KIND_LOCAL, repo=None):
    """Validate an index document; raises IndexValidationError listing every problem found."""
    problems = []
    if not isinstance(doc, dict):
        raise IndexValidationError(["document must be a JSON object"])
    if doc.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"'schema_version' must be {SCHEMA_VERSION}, found {doc.get('schema_version')!r}")
    interfaces = doc.get("interfaces")
    if not isinstance(interfaces, dict):
        problems.append("'interfaces' must be an object keyed on canonical interface names")
        interfaces = {}
    for key, entries in interfaces.items():
        if not isinstance(key, str) or not key:
            problems.append(f"interface key {key!r} must be a non-empty string")
            continue
        if not isinstance(entries, list) or not entries:
            problems.append(f"interfaces[{key!r}] must be a non-empty list; empty keys must be removed")
            continue
        seen_types = set()
        for i, entry in enumerate(entries):
            _validate_interface_object(entry, f"interfaces[{key!r}][{i}]", kind, repo, problems)
            if isinstance(entry, dict) and isinstance(entry.get("type"), str):
                if entry["type"] in seen_types:
                    problems.append(f"interfaces[{key!r}]: duplicate interface object for type '{entry['type']}'")
                seen_types.add(entry["type"])
    if kind == KIND_COMPILED:
        conflicts = doc.get("conflicts")
        if not isinstance(conflicts, list):
            problems.append("compiled index needs a 'conflicts' list")
        else:
            for i, conflict in enumerate(conflicts):
                _validate_conflict(conflict, f"conflicts[{i}]", problems)
        unknown = set(doc) - {"schema_version", "interfaces", "conflicts"}
    else:
        if "conflicts" in doc:
            problems.append(f"{kind} indexes must not contain 'conflicts' — conflicts exist only in the instance repo")
        unknown = set(doc) - {"schema_version", "interfaces"}
    if unknown:
        problems.append(f"unknown top-level fields {sorted(unknown)}")
    if problems:
        raise IndexValidationError(problems)
    return doc


def _owner_sort_key(owner):
    return (owner["repo"], owner["component"]) if owner else ("", "")


def sorted_doc(doc):
    """Return a copy with every list deterministically ordered (dict keys are sorted at dump time)."""
    out = {"schema_version": doc["schema_version"], "interfaces": {}}
    for key in sorted(doc.get("interfaces", {})):
        entries = []
        for entry in doc["interfaces"][key]:
            new_entry = dict(entry)
            for role in ("consumer", "producer"):
                new_entry[role] = sorted(
                    ({**robj, "source_files": sorted(set(robj["source_files"]))} for robj in entry[role]),
                    key=lambda r: r["repo"],
                )
            entries.append(new_entry)
        out["interfaces"][key] = sorted(entries, key=lambda e: (e["type"], _owner_sort_key(e.get("owner"))))
    if "conflicts" in doc:
        out["conflicts"] = sorted(
            (
                {**c, "claims": sorted(c["claims"], key=lambda cl: cl["claimed_by"])}
                for c in doc["conflicts"]
            ),
            key=lambda c: (c["name"], c["type"], c["reason"]),
        )
    return out


def dumps_index(doc):
    """Serialize deterministically: sorted structures, 2-space indent, trailing newline."""
    return json.dumps(sorted_doc(doc), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def save_index(doc, path, kind=KIND_LOCAL, repo=None):
    validate_index(doc, kind=kind, repo=repo)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_index(doc), encoding="utf-8")
    return path


def load_index(path, kind=KIND_LOCAL, repo=None):
    path = Path(path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise IndexValidationError([f"index file not found: {path}"])
    except json.JSONDecodeError as exc:
        raise IndexValidationError([f"{path} is not valid JSON: {exc}"])
    return validate_index(doc, kind=kind, repo=repo)
