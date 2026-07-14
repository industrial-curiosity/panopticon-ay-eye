"""Dependency index documents: schema, load, validate, save.

Tracks internal (same-org) library/package dependencies as their own relationship, separate from
the interface-indexing capability's ``interfaces/`` files (see ``panopticon/index.py``) — a
dependency has exactly one publisher (self-registered) and many importers, and importers record
*which* modules they import, which the interface schema's repo objects have no field for.

One JSON schema serves all three index kinds, mirroring ``panopticon/index.py``:

- **local** index — ``panopticon/dependencies.json`` in a child repo
- **shard** — ``dependencies/{repo}.json`` in the instance repo
- **compiled** index — ``dependencies/index.json`` in the instance repo

Document shape::

    {
      "schema_version": 1,
      "dependencies": {
        "<canonical-name>": [
          {
            "owner": {"repo": "acme-auth-lib", "component": null},   # or null
            "ecosystem": "go",
            "consumer": [{"repo": "svc-b", "source_files": ["go.mod"], "apis": ["acme-auth-lib/client"]}],
            "producer": [{"repo": "acme-auth-lib", "source_files": ["go.mod"]}],
            "links_to_interface": {"name": "orders-api", "type": "rest"},   # optional, hint-only
            "extracted_by": "llm"                                          # optional provenance tag
          }
        ]
      },
      "conflicts": []   # compiled index only, recomputed on every rebuild
    }

``apis`` is valid only on consumer repo objects (import-level granularity — which modules/packages a
repo imports from the dependency, not which interface types get called). ``links_to_interface`` is set
only via an explicit ``panopticon-dependency-of`` hint (see ``panopticon/naming.py``) — no naming
heuristic infers it automatically.

Saving is deterministic (sorted keys, sorted lists, fixed indentation) so the compiled-index rebuild is
byte-identical for identical shards, matching ``panopticon/index.py``.
"""

import json
from pathlib import Path

from . import SCHEMA_VERSION

KIND_LOCAL = "local"
KIND_SHARD = "shard"
KIND_COMPILED = "compiled"

CONFLICT_REASON_OWNERSHIP_DISPUTE = "ownership-dispute"
CONFLICT_REASON_UNREGISTERED_PRODUCER = "unregistered-producer"
CONFLICT_REASONS = (CONFLICT_REASON_OWNERSHIP_DISPUTE, CONFLICT_REASON_UNREGISTERED_PRODUCER)


class DependencyIndexValidationError(Exception):
    """Raised when a dependency index document does not satisfy the schema."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("invalid dependency index document:\n" + "\n".join(f"- {p}" for p in self.problems))


def empty_index(kind=KIND_LOCAL):
    doc = {"schema_version": SCHEMA_VERSION, "dependencies": {}}
    if kind == KIND_COMPILED:
        doc["conflicts"] = []
    return doc


def _validate_repo_object(obj, where, role, problems):
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
    allowed = {"repo", "source_files", "extracted_by"}
    if role == "consumer":
        allowed = allowed | {"apis"}
        if "apis" in obj:
            apis = obj["apis"]
            if not isinstance(apis, list) or not all(isinstance(a, str) and a for a in apis):
                problems.append(f"{where}: 'apis' must be a list of non-empty strings")
    unknown = set(obj) - allowed
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
    if not isinstance(owner.get("component"), str) and owner.get("component") is not None:
        problems.append(f"{where}: owner 'component' must be a string or null")
    unknown = set(owner) - {"repo", "component"}
    if unknown:
        problems.append(f"{where}: unknown owner fields {sorted(unknown)}")


def _validate_links_to_interface(link, where, problems):
    if link is None:
        return
    if not isinstance(link, dict):
        problems.append(f"{where}: 'links_to_interface' must be an object")
        return
    for field in ("name", "type"):
        if not isinstance(link.get(field), str) or not link[field]:
            problems.append(f"{where}.links_to_interface: needs a non-empty '{field}' string")
    unknown = set(link) - {"name", "type"}
    if unknown:
        problems.append(f"{where}.links_to_interface: unknown fields {sorted(unknown)}")


def _validate_dependency_object(entry, where, kind, repo, problems):
    if not isinstance(entry, dict):
        problems.append(f"{where}: dependency object must be an object")
        return
    if not isinstance(entry.get("ecosystem"), str) or not entry["ecosystem"]:
        problems.append(f"{where}: needs a non-empty 'ecosystem' string")
    _validate_owner(entry.get("owner"), where, problems)
    if "links_to_interface" in entry:
        _validate_links_to_interface(entry.get("links_to_interface"), where, problems)
    empty = True
    for role in ("consumer", "producer"):
        role_list = entry.get(role)
        if not isinstance(role_list, list):
            problems.append(f"{where}: '{role}' must be a list of repo objects")
            continue
        seen = set()
        for i, robj in enumerate(role_list):
            _validate_repo_object(robj, f"{where}.{role}[{i}]", role, problems)
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
    unknown = set(entry) - {"owner", "ecosystem", "consumer", "producer", "extracted_by", "links_to_interface"}
    if unknown:
        problems.append(f"{where}: unknown dependency-object fields {sorted(unknown)}")


def _validate_conflict(conflict, where, problems):
    if not isinstance(conflict, dict):
        problems.append(f"{where}: conflict entry must be an object")
        return
    for field in ("name", "ecosystem", "reason", "details"):
        if not isinstance(conflict.get(field), str) or not conflict[field]:
            problems.append(f"{where}: needs a non-empty '{field}' string")
    reason = conflict.get("reason")
    if reason not in CONFLICT_REASONS:
        problems.append(f"{where}: 'reason' must be one of {list(CONFLICT_REASONS)}")
    claims = conflict.get("claims")
    if not isinstance(claims, list):
        problems.append(f"{where}: 'claims' must be a list")
    else:
        if reason == CONFLICT_REASON_OWNERSHIP_DISPUTE and not claims:
            problems.append(f"{where}: 'claims' must be non-empty for reason '{CONFLICT_REASON_OWNERSHIP_DISPUTE}'")
        for i, claim in enumerate(claims):
            if not isinstance(claim, dict) or not isinstance(claim.get("claimed_by"), str):
                problems.append(f"{where}.claims[{i}]: needs a 'claimed_by' repo string")
            else:
                _validate_owner(claim.get("owner"), f"{where}.claims[{i}]", problems)
    unknown = set(conflict) - {"name", "ecosystem", "reason", "details", "claims"}
    if unknown:
        problems.append(f"{where}: unknown conflict fields {sorted(unknown)}")


def validate_index(doc, kind=KIND_LOCAL, repo=None):
    """Validate a dependency index document; raises DependencyIndexValidationError listing every problem."""
    problems = []
    if not isinstance(doc, dict):
        raise DependencyIndexValidationError(["document must be a JSON object"])
    if doc.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"'schema_version' must be {SCHEMA_VERSION}, found {doc.get('schema_version')!r}")
    dependencies = doc.get("dependencies")
    if not isinstance(dependencies, dict):
        problems.append("'dependencies' must be an object keyed on canonical dependency names")
        dependencies = {}
    for key, entries in dependencies.items():
        if not isinstance(key, str) or not key:
            problems.append(f"dependency key {key!r} must be a non-empty string")
            continue
        if not isinstance(entries, list) or not entries:
            problems.append(f"dependencies[{key!r}] must be a non-empty list; empty keys must be removed")
            continue
        seen_ecosystems = set()
        for i, entry in enumerate(entries):
            _validate_dependency_object(entry, f"dependencies[{key!r}][{i}]", kind, repo, problems)
            if isinstance(entry, dict) and isinstance(entry.get("ecosystem"), str):
                if entry["ecosystem"] in seen_ecosystems:
                    problems.append(f"dependencies[{key!r}]: duplicate dependency object for ecosystem '{entry['ecosystem']}'")
                seen_ecosystems.add(entry["ecosystem"])
    if kind == KIND_COMPILED:
        conflicts = doc.get("conflicts")
        if not isinstance(conflicts, list):
            problems.append("compiled index needs a 'conflicts' list")
        else:
            for i, conflict in enumerate(conflicts):
                _validate_conflict(conflict, f"conflicts[{i}]", problems)
        unknown = set(doc) - {"schema_version", "dependencies", "conflicts"}
    else:
        if "conflicts" in doc:
            problems.append(f"{kind} indexes must not contain 'conflicts' — conflicts exist only in the instance repo")
        unknown = set(doc) - {"schema_version", "dependencies"}
    if unknown:
        problems.append(f"unknown top-level fields {sorted(unknown)}")
    if problems:
        raise DependencyIndexValidationError(problems)
    return doc


def _owner_sort_key(owner):
    return (owner["repo"], owner.get("component") or "") if owner else ("", "")


def sorted_doc(doc):
    """Return a copy with every list deterministically ordered (dict keys sorted at dump time)."""
    out = {"schema_version": doc["schema_version"], "dependencies": {}}
    for key in sorted(doc.get("dependencies", {})):
        entries = []
        for entry in doc["dependencies"][key]:
            new_entry = dict(entry)
            for role in ("consumer", "producer"):
                sorted_role = []
                for robj in entry[role]:
                    new_robj = {**robj, "source_files": sorted(set(robj["source_files"]))}
                    if "apis" in robj:
                        new_robj["apis"] = sorted(set(robj["apis"]))
                    sorted_role.append(new_robj)
                new_entry[role] = sorted(sorted_role, key=lambda r: r["repo"])
            entries.append(new_entry)
        out["dependencies"][key] = sorted(entries, key=lambda e: (e["ecosystem"], _owner_sort_key(e.get("owner"))))
    if "conflicts" in doc:
        out["conflicts"] = sorted(
            (
                {**c, "claims": sorted(c["claims"], key=lambda cl: cl["claimed_by"])}
                for c in doc["conflicts"]
            ),
            key=lambda c: (c["name"], c["ecosystem"], c["reason"]),
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
        raise DependencyIndexValidationError([f"dependency index file not found: {path}"])
    except json.JSONDecodeError as exc:
        raise DependencyIndexValidationError([f"{path} is not valid JSON: {exc}"])
    return validate_index(doc, kind=kind, repo=repo)
