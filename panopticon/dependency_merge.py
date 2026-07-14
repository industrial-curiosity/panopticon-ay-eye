"""Dependency-indexing capability: shard replace, compiled-index rebuild, conflict detection, and
merge simulation — mirroring panopticon/merge.py's shape for the dependency schema
(panopticon/dependencies.py), entirely independent of the interface merge path (own files,
``dependencies/`` in the instance repo, never touching ``interfaces/``).

Conflict detection differs from the interface capability in one structural way: a dependency has
exactly one producer *role* (self-registration), so there is no dependency equivalent of
``owner-attribution-mismatch`` (interfaces: repos disagreeing about a *third party's* ownership).
Nothing in this codebase's extraction path (parsers, LLM fallback skill) ever sets a dependency
shard's ``owner`` to a repo other than the shard's own — see ``dependency_extraction.py`` and the
panopticon-dependency-extraction skill, both of which only set ``owned``/``owner`` from a
self-registering producer. Owner resolution below therefore only reconciles *self*-claims
(``ownership-dispute``: two or more repos each claim themselves); a non-self claim, if one somehow
existed in a hand-edited shard, is intentionally ignored rather than invented into a third conflict
category. The dependency-specific ``unregistered-producer`` reason instead comes directly from the
folded ``producer`` list being empty after union — no repo has self-registered — independent of
owner-claim resolution.

``merge_into_instance`` below also rebuilds the org diagram, the same way
``merge.merge_into_instance`` does (design D3) — both merge paths call the same
``diagrams.write_org_diagram(instance_root, ...)``, which reads *both* compiled indices fresh from
disk rather than accepting an in-memory doc from whichever path triggered it, so either merge path
always renders the other index's current state too, never a stale one.
"""

import argparse
import sys
from pathlib import Path

from . import SCHEMA_VERSION
from .config import ConfigError, load_diagram_config, require_supported_diagram_format
from .diagrams import write_org_diagram
from .dependencies import (
    CONFLICT_REASON_OWNERSHIP_DISPUTE,
    CONFLICT_REASON_UNREGISTERED_PRODUCER,
    DependencyIndexValidationError,
    KIND_COMPILED,
    KIND_LOCAL,
    KIND_SHARD,
    dumps_index,
    empty_index,
    load_index,
    save_index,
    sorted_doc,
    validate_index,
)
from .report import format_operational_failure

COMPILED_BASENAME = "index.json"
DEPENDENCIES_DIR = "dependencies"


def _fold_repo_objects(target, additions):
    """Union repo objects into target, merging source-file (and, for consumers, apis) lists per
    repo. Mirrors merge.py's ``_fold_repo_objects`` exactly, plus the ``apis`` union."""
    by_repo = {robj["repo"]: dict(robj) for robj in target}
    for robj in additions:
        existing = by_repo.get(robj["repo"])
        if existing is None:
            by_repo[robj["repo"]] = dict(robj)
        else:
            existing["source_files"] = sorted(set(existing["source_files"]) | set(robj["source_files"]))
            if "apis" in robj or "apis" in existing:
                existing["apis"] = sorted(set(existing.get("apis", [])) | set(robj.get("apis", [])))
            if robj.get("extracted_by"):
                existing["extracted_by"] = robj["extracted_by"]
    return [by_repo[name] for name in sorted(by_repo)]


def _owner_key(owner):
    return (owner["repo"], owner.get("component")) if owner else None


def _conflict(name, ecosystem, reason, claims, details):
    return {
        "name": name,
        "ecosystem": ecosystem,
        "reason": reason,
        "claims": [
            {"claimed_by": repo, "owner": owner}
            for repo, owner in sorted(claims.items())
        ],
        "details": details,
    }


def _resolve_owner(name, ecosystem, claims):
    """Resolve one dependency object's owner from per-repo claims; returns (owner, conflicts).

    Only self-claims (a repo claiming itself) are reconciled — see the module docstring for why a
    dependency has no attribution-mismatch category. A non-self claim is ignored, not surfaced.
    """
    self_claims = {repo: owner for repo, owner in claims.items() if owner and owner["repo"] == repo}
    if len(self_claims) > 1:
        conflict = _conflict(
            name,
            ecosystem,
            CONFLICT_REASON_OWNERSHIP_DISPUTE,
            self_claims,
            f"repos {sorted(self_claims)} each claim ownership of '{name}' ({ecosystem})",
        )
        return None, [conflict]
    if len(self_claims) == 1:
        ((_, owner),) = self_claims.items()
        return owner, []
    return None, []


def compile_index(shards):
    """Deterministically rebuild the compiled dependency index from ``{repo_name: shard_doc}``.
    LLM-free, mirroring merge.py's ``compile_index``."""
    folded = {}
    claims = {}
    for repo in sorted(shards):
        shard = shards[repo]
        for name, entries in shard.get("dependencies", {}).items():
            for entry in entries:
                ident = (name, entry["ecosystem"])
                target = folded.setdefault(
                    ident, {"ecosystem": entry["ecosystem"], "consumer": [], "producer": []}
                )
                for role in ("consumer", "producer"):
                    additions = entry[role]
                    if entry.get("extracted_by"):
                        additions = [
                            {**robj, "extracted_by": entry["extracted_by"]} for robj in additions
                        ]
                    target[role] = _fold_repo_objects(target[role], additions)
                if entry.get("links_to_interface"):
                    target.setdefault("_links_to_interface_claims", []).append(entry["links_to_interface"])
                claims.setdefault(ident, {})[repo] = entry.get("owner")
    compiled = empty_index(KIND_COMPILED)
    for (name, ecosystem), entry in folded.items():
        if not entry["consumer"] and not entry["producer"]:
            continue
        owner, conflicts = _resolve_owner(name, ecosystem, claims[(name, ecosystem)])
        entry["owner"] = owner
        link_claims = entry.pop("_links_to_interface_claims", [])
        if link_claims:
            # All repos linking the same dependency name are expected to agree; the first-seen,
            # deterministically-sorted claim wins rather than treating disagreement as a new
            # conflict category not scoped for this change (open question, design.md).
            entry["links_to_interface"] = sorted(
                link_claims, key=lambda link: (link["name"], link["type"])
            )[0]
        if not entry["producer"]:
            conflicts.append(
                _conflict(
                    name, ecosystem, CONFLICT_REASON_UNREGISTERED_PRODUCER, {},
                    f"'{name}' ({ecosystem}) has consumer(s) but no repo has self-registered as its producer",
                )
            )
        compiled["dependencies"].setdefault(name, []).append(entry)
        compiled["conflicts"].extend(conflicts)
    compiled = sorted_doc(compiled)
    validate_index(compiled, kind=KIND_COMPILED)
    return compiled


def shards_from_compiled(compiled):
    """Derive per-repo shard documents from a compiled dependency index (inverse of
    ``compile_index``), mirroring merge.py's ``shards_from_compiled``."""
    conflict_claims = {}
    for conflict in compiled.get("conflicts", []):
        if conflict["reason"] != CONFLICT_REASON_OWNERSHIP_DISPUTE:
            continue
        ident = (conflict["name"], conflict["ecosystem"])
        for claim in conflict["claims"]:
            conflict_claims.setdefault(ident, {})[claim["claimed_by"]] = claim["owner"]
    shards = {}
    for name, entries in compiled.get("dependencies", {}).items():
        for entry in entries:
            ident = (name, entry["ecosystem"])
            repos = {}
            for role in ("consumer", "producer"):
                for robj in entry[role]:
                    shard_robj = {"repo": robj["repo"], "source_files": list(robj["source_files"])}
                    if "apis" in robj:
                        shard_robj["apis"] = list(robj["apis"])
                    repos.setdefault(robj["repo"], {"consumer": [], "producer": []})[role].append(shard_robj)
                    if robj.get("extracted_by"):
                        repos[robj["repo"]]["extracted_by"] = robj["extracted_by"]
            for repo, roles in repos.items():
                overrides = conflict_claims.get(ident, {})
                owner = overrides[repo] if repo in overrides else entry.get("owner")
                shard_entry = {
                    "owner": owner,
                    "ecosystem": entry["ecosystem"],
                    "consumer": roles["consumer"],
                    "producer": roles["producer"],
                }
                if entry.get("links_to_interface"):
                    shard_entry["links_to_interface"] = entry["links_to_interface"]
                if roles.get("extracted_by"):
                    shard_entry["extracted_by"] = roles["extracted_by"]
                shard = shards.setdefault(repo, empty_index(KIND_SHARD))
                shard["dependencies"].setdefault(name, []).append(shard_entry)
    return {repo: sorted_doc(doc) for repo, doc in shards.items()}


def replace_shard(shards, repo, local_doc):
    """Whole-shard replace: the repo re-asserts everything it knows; an empty index removes it."""
    new_shards = {name: doc for name, doc in shards.items() if name != repo}
    if local_doc.get("dependencies"):
        validate_index(local_doc, kind=KIND_SHARD, repo=repo)
        new_shards[repo] = sorted_doc(local_doc)
    return new_shards


def _object_map(doc):
    return {
        (name, entry["ecosystem"]): entry
        for name, entries in doc.get("dependencies", {}).items()
        for entry in entries
    }


def _conflict_ids(doc):
    return {(c["name"], c["ecosystem"], c["reason"]): c for c in doc.get("conflicts", [])}


def diff_compiled(before, after, repo):
    """Report structure shared by merge and simulation, mirroring merge.py's ``diff_compiled``."""
    before_objects, after_objects = _object_map(before), _object_map(after)
    before_conflicts, after_conflicts = _conflict_ids(before), _conflict_ids(after)

    def idents(keys):
        return [{"name": name, "ecosystem": ecosystem} for name, ecosystem in sorted(keys)]

    changed = [
        ident
        for ident in before_objects.keys() & after_objects.keys()
        if before_objects[ident] != after_objects[ident]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "repo": repo,
        "added": idents(after_objects.keys() - before_objects.keys()),
        "removed": idents(before_objects.keys() - after_objects.keys()),
        "changed": idents(changed),
        "conflicts": {
            "new": [after_conflicts[k] for k in sorted(after_conflicts.keys() - before_conflicts.keys())],
            "resolved": [before_conflicts[k] for k in sorted(before_conflicts.keys() - after_conflicts.keys())],
            "unchanged": [after_conflicts[k] for k in sorted(after_conflicts.keys() & before_conflicts.keys())],
        },
    }


def simulate_merge(local_doc, compiled_doc, repo):
    """Dry-run of the merge over two JSON documents; returns the merge report."""
    validate_index(compiled_doc, kind=KIND_COMPILED)
    shards = replace_shard(shards_from_compiled(compiled_doc), repo, local_doc)
    return diff_compiled(compiled_doc, compile_index(shards), repo)


def load_shards(instance_root):
    dependencies_dir = Path(instance_root) / DEPENDENCIES_DIR
    shards = {}
    if not dependencies_dir.is_dir():
        return shards
    for path in sorted(dependencies_dir.glob("*.json")):
        if path.name == COMPILED_BASENAME:
            continue
        repo = path.stem
        shards[repo] = load_index(path, kind=KIND_SHARD, repo=repo)
    return shards


def merge_into_instance(instance_root, repo, local_doc):
    """Replace the repo's dependency shard on disk, rebuild the compiled dependency index, rebuild
    the org diagram (module docstring — shared with merge.merge_into_instance), and return the
    merge report."""
    instance_root = Path(instance_root)
    dependencies_dir = instance_root / DEPENDENCIES_DIR
    compiled_path = dependencies_dir / COMPILED_BASENAME
    if compiled_path.exists():
        before = load_index(compiled_path, kind=KIND_COMPILED)
    else:
        before = empty_index(KIND_COMPILED)
    shards = replace_shard(load_shards(instance_root), repo, local_doc)
    after = compile_index(shards)
    shard_path = dependencies_dir / f"{repo}.json"
    if repo in shards:
        save_index(shards[repo], shard_path, kind=KIND_SHARD, repo=repo)
    elif shard_path.exists():
        shard_path.unlink()
    dependencies_dir.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text(dumps_index(after), encoding="utf-8")
    diagram_format = load_diagram_config(instance_root)["format"]
    require_supported_diagram_format(diagram_format)
    write_org_diagram(instance_root, diagram_format)
    return diff_compiled(before, after, repo)


def _format_conflict(conflict):
    claims = "; ".join(
        f"`{claim['claimed_by']}` → "
        + (f"{claim['owner']['repo']}/{claim['owner']['component']}" if claim["owner"] else "null")
        for claim in conflict["claims"]
    ) or "none"
    return (
        f"- **`{conflict['name']}` ({conflict['ecosystem']})** — {conflict['reason']}: "
        f"{conflict['details']} (claims: {claims})"
    )


def format_report(report, simulated=True):
    """Markdown rendering of a merge/simulation report for PR comments and CI summaries."""
    verb = "would create" if simulated else "created"
    title = "Panopticon dependency pre-merge simulation" if simulated else "Panopticon dependency merge"
    new_conflicts = report["conflicts"]["new"]
    unchanged = report["conflicts"]["unchanged"]
    resolved = report["conflicts"]["resolved"]
    lines = []
    if new_conflicts:
        lines.append(f"⚠️ **{title}: this change {verb} {len(new_conflicts)} dependency conflict(s).**")
        lines.append("")
        lines.extend(_format_conflict(c) for c in new_conflicts)
        lines.append("")
        lines.append(
            "Resolve by adding `panopticon-dependency` hints where internality/naming is ambiguous, or "
            "confirming the producer repo has self-registered (panopticon-dependency-naming skill)."
        )
    else:
        lines.append(f"✅ **{title}: no new dependency conflicts.**")
    if resolved:
        lines.append("")
        lines.append(f"Resolves {len(resolved)} existing conflict(s): " + ", ".join(f"`{c['name']}`" for c in resolved))
    if unchanged:
        lines.append("")
        lines.append(f"{len(unchanged)} pre-existing conflict(s) remain: " + ", ".join(f"`{c['name']}`" for c in unchanged))
    changes = []
    for label in ("added", "removed", "changed"):
        if report[label]:
            changes.append(f"{label}: " + ", ".join(f"`{i['name']}` ({i['ecosystem']})" for i in report[label]))
    if changes:
        lines.append("")
        lines.append("Index impact — " + "; ".join(changes))
    return "\n".join(lines)


def collect_actions(report):
    """Structured remediation actions for the combined-report TL;DR (panopticon/report.py)."""
    actions = [
        {"kind": "resolve_conflict", "target": c["name"]}
        for c in report["conflicts"]["new"]
    ]
    if actions:
        actions.append({"kind": "commit_and_push"})
    return actions


def _write_report(report, args, simulated):
    import json as _json

    text = format_report(report, simulated=simulated)
    print(text)
    if args.report_file:
        Path(args.report_file).write_text(text + "\n", encoding="utf-8")
    if args.json_report:
        Path(args.json_report).write_text(_json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.actions_file:
        Path(args.actions_file).write_text(_json.dumps(collect_actions(report)), encoding="utf-8")
    return 2 if report["conflicts"]["new"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Panopticon dependency shard merge and pre-merge simulation.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("simulate", "dry-run merge report"), ("merge", "replace shard and rebuild")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--local", required=True, help="child repo local dependency index (panopticon/dependencies.json)")
        cmd.add_argument("--repo", required=True, help="child repo name")
        cmd.add_argument("--report-file", help="write the markdown report here")
        cmd.add_argument("--json-report", help="write the raw report JSON here")
        cmd.add_argument("--actions-file", help="write the structured TL;DR actions JSON here")
    sub.choices["simulate"].add_argument("--compiled", required=True, help="instance compiled dependency index")
    sub.choices["merge"].add_argument("--instance-root", required=True, help="instance repo checkout")
    args = parser.parse_args(argv)

    try:
        local_doc = load_index(args.local, kind=KIND_LOCAL, repo=args.repo)
        if args.command == "simulate":
            compiled = load_index(args.compiled, kind=KIND_COMPILED)
            report = simulate_merge(local_doc, compiled, args.repo)
        else:
            report = merge_into_instance(args.instance_root, args.repo, local_doc)
    except (DependencyIndexValidationError, ConfigError) as exc:
        label = "dependency pre-merge simulation" if args.command == "simulate" else "dependency merge"
        print(f"::error::Panopticon {label} could not run: {exc}")
        if args.report_file:
            Path(args.report_file).write_text(format_operational_failure(label, str(exc)) + "\n",
                                               encoding="utf-8")
        return 1
    return _write_report(report, args, simulated=(args.command == "simulate"))


if __name__ == "__main__":
    sys.exit(main())
