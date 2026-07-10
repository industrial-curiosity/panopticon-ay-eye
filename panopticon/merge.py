"""Shard replace, compiled-index rebuild, conflict detection, and merge simulation.

The real merge and the pre-merge simulation share one code path (design D4):

- real merge: read shards from ``interfaces/`` in an instance-repo checkout, replace the merging
  repo's shard wholesale, ``compile_index`` over all shards, write the compiled index.
- simulation: derive per-repo pseudo-shards from the compiled index alone
  (``shards_from_compiled`` — the compiled index plus its ``claims``-bearing conflict entries
  carry full provenance, so the derivation is lossless), replace the repo's shard in memory, and
  run the same ``compile_index``.

Both paths end in ``diff_compiled`` producing the same report structure, so what PRs predict is
what merges do.

Conflict entries are recomputed deterministically on every rebuild and exist only in the compiled
index. Two reasons are detected:

- ``ownership-dispute`` — two or more repos claim themselves as owner of one interface object.
- ``owner-attribution-mismatch`` — repos attribute ownership to different repos (no dispute
  between self-claims, but the org's picture of who owns the interface disagrees).
"""

import argparse
import sys
from pathlib import Path

from . import SCHEMA_VERSION
from .index import (
    IndexValidationError,
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
INTERFACES_DIR = "interfaces"


def _fold_repo_objects(target, additions):
    """Union repo objects into target, merging source-file lists per repo."""
    by_repo = {robj["repo"]: dict(robj) for robj in target}
    for robj in additions:
        existing = by_repo.get(robj["repo"])
        if existing is None:
            by_repo[robj["repo"]] = dict(robj)
        else:
            existing["source_files"] = sorted(set(existing["source_files"]) | set(robj["source_files"]))
            if robj.get("extracted_by"):
                existing["extracted_by"] = robj["extracted_by"]
    return [by_repo[name] for name in sorted(by_repo)]


def _owner_key(owner):
    return (owner["repo"], owner["component"]) if owner else None


def _conflict(name, iface_type, reason, claims, details):
    return {
        "name": name,
        "type": iface_type,
        "reason": reason,
        "claims": [
            {"claimed_by": repo, "owner": owner}
            for repo, owner in sorted(claims.items())
        ],
        "details": details,
    }


def _resolve_owner(name, iface_type, claims):
    """Resolve one interface object's owner from per-repo claims; returns (owner, conflicts)."""
    self_claims = {repo: owner for repo, owner in claims.items() if owner and owner["repo"] == repo}
    non_null = {repo: owner for repo, owner in claims.items() if owner}
    conflicts = []
    if len(self_claims) > 1:
        conflicts.append(
            _conflict(
                name,
                iface_type,
                "ownership-dispute",
                self_claims,
                f"repos {sorted(self_claims)} each claim ownership of '{name}' ({iface_type})",
            )
        )
        return None, conflicts
    if len(self_claims) == 1:
        ((owner_repo, owner),) = self_claims.items()
        disagreeing = {r: o for r, o in non_null.items() if _owner_key(o) != _owner_key(owner)}
        if disagreeing:
            claimants = {**disagreeing, owner_repo: owner}
            conflicts.append(
                _conflict(
                    name,
                    iface_type,
                    "owner-attribution-mismatch",
                    claimants,
                    f"repos {sorted(disagreeing)} attribute '{name}' ({iface_type}) differently "
                    f"from its owner '{owner['repo']}'",
                )
            )
        return owner, conflicts
    distinct = {_owner_key(o): o for o in non_null.values()}
    if len(distinct) == 1:
        return next(iter(distinct.values())), conflicts
    if len(distinct) > 1:
        conflicts.append(
            _conflict(
                name,
                iface_type,
                "owner-attribution-mismatch",
                non_null,
                f"repos {sorted(non_null)} attribute ownership of '{name}' ({iface_type}) to "
                "different owners",
            )
        )
    return None, conflicts


def compile_index(shards):
    """Deterministically rebuild the compiled index from ``{repo_name: shard_doc}``. LLM-free."""
    folded = {}
    claims = {}
    for repo in sorted(shards):
        shard = shards[repo]
        for name, entries in shard.get("interfaces", {}).items():
            for entry in entries:
                ident = (name, entry["type"])
                target = folded.setdefault(
                    ident, {"type": entry["type"], "consumer": [], "producer": []}
                )
                for role in ("consumer", "producer"):
                    additions = entry[role]
                    if entry.get("extracted_by"):
                        additions = [
                            {**robj, "extracted_by": entry["extracted_by"]} for robj in additions
                        ]
                    target[role] = _fold_repo_objects(target[role], additions)
                claims.setdefault(ident, {})[repo] = entry.get("owner")
    compiled = empty_index(KIND_COMPILED)
    for (name, iface_type), entry in folded.items():
        if not entry["consumer"] and not entry["producer"]:
            continue
        owner, conflicts = _resolve_owner(name, iface_type, claims[(name, iface_type)])
        entry["owner"] = owner
        compiled["interfaces"].setdefault(name, []).append(entry)
        compiled["conflicts"].extend(conflicts)
    compiled = sorted_doc(compiled)
    validate_index(compiled, kind=KIND_COMPILED)
    return compiled


def shards_from_compiled(compiled):
    """Derive per-repo shard documents from a compiled index (inverse of compile_index).

    Owner claims are reconstructed from the resolved owner for clean objects and from conflict
    entries' ``claims`` for disputed/mismatched ones, so ``compile_index(shards_from_compiled(c))``
    reproduces ``c`` byte-identically — the property that keeps simulation on the merge code path.
    """
    conflict_claims = {}
    for conflict in compiled.get("conflicts", []):
        ident = (conflict["name"], conflict["type"])
        for claim in conflict["claims"]:
            conflict_claims.setdefault(ident, {})[claim["claimed_by"]] = claim["owner"]
    shards = {}
    for name, entries in compiled.get("interfaces", {}).items():
        for entry in entries:
            ident = (name, entry["type"])
            repos = {}
            for role in ("consumer", "producer"):
                for robj in entry[role]:
                    repos.setdefault(robj["repo"], {"consumer": [], "producer": []})[role].append(
                        {"repo": robj["repo"], "source_files": list(robj["source_files"])}
                    )
                    if robj.get("extracted_by"):
                        repos[robj["repo"]]["extracted_by"] = robj["extracted_by"]
            for repo, roles in repos.items():
                overrides = conflict_claims.get(ident, {})
                if repo in overrides:
                    owner = overrides[repo]
                else:
                    owner = entry.get("owner")
                shard_entry = {
                    "owner": owner,
                    "type": entry["type"],
                    "consumer": roles["consumer"],
                    "producer": roles["producer"],
                }
                if roles.get("extracted_by"):
                    shard_entry["extracted_by"] = roles["extracted_by"]
                shard = shards.setdefault(repo, empty_index(KIND_SHARD))
                shard["interfaces"].setdefault(name, []).append(shard_entry)
    return {repo: sorted_doc(doc) for repo, doc in shards.items()}


def replace_shard(shards, repo, local_doc):
    """Whole-shard replace: the repo re-asserts everything it knows; an empty index removes it."""
    new_shards = {name: doc for name, doc in shards.items() if name != repo}
    if local_doc.get("interfaces"):
        validate_index(local_doc, kind=KIND_SHARD, repo=repo)
        new_shards[repo] = sorted_doc(local_doc)
    return new_shards


def _object_map(doc):
    return {
        (name, entry["type"]): entry
        for name, entries in doc.get("interfaces", {}).items()
        for entry in entries
    }


def _conflict_ids(doc):
    return {(c["name"], c["type"], c["reason"]): c for c in doc.get("conflicts", [])}


def diff_compiled(before, after, repo):
    """Report structure shared by merge and simulation."""
    before_objects, after_objects = _object_map(before), _object_map(after)
    before_conflicts, after_conflicts = _conflict_ids(before), _conflict_ids(after)

    def idents(keys):
        return [{"name": name, "type": iface_type} for name, iface_type in sorted(keys)]

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
    """Dry-run of the merge over two JSON documents; returns the merge report (design D4)."""
    validate_index(compiled_doc, kind=KIND_COMPILED)
    shards = replace_shard(shards_from_compiled(compiled_doc), repo, local_doc)
    return diff_compiled(compiled_doc, compile_index(shards), repo)


def load_shards(instance_root):
    interfaces_dir = Path(instance_root) / INTERFACES_DIR
    shards = {}
    for path in sorted(interfaces_dir.glob("*.json")):
        if path.name == COMPILED_BASENAME:
            continue
        repo = path.stem
        shards[repo] = load_index(path, kind=KIND_SHARD, repo=repo)
    return shards


def merge_into_instance(instance_root, repo, local_doc):
    """Replace the repo's shard on disk, rebuild the compiled index, and return the merge report."""
    instance_root = Path(instance_root)
    interfaces_dir = instance_root / INTERFACES_DIR
    compiled_path = interfaces_dir / COMPILED_BASENAME
    if compiled_path.exists():
        before = load_index(compiled_path, kind=KIND_COMPILED)
    else:
        before = empty_index(KIND_COMPILED)
    shards = replace_shard(load_shards(instance_root), repo, local_doc)
    after = compile_index(shards)
    shard_path = interfaces_dir / f"{repo}.json"
    if repo in shards:
        save_index(shards[repo], shard_path, kind=KIND_SHARD, repo=repo)
    elif shard_path.exists():
        shard_path.unlink()
    interfaces_dir.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text(dumps_index(after), encoding="utf-8")
    return diff_compiled(before, after, repo)


def _format_conflict(conflict):
    claims = "; ".join(
        f"`{claim['claimed_by']}` → "
        + (f"{claim['owner']['repo']}/{claim['owner']['component']}" if claim["owner"] else "null")
        for claim in conflict["claims"]
    )
    return (
        f"- **`{conflict['name']}` ({conflict['type']})** — {conflict['reason']}: "
        f"{conflict['details']} (claims: {claims})"
    )


def format_report(report, simulated=True):
    """Markdown rendering of a merge/simulation report for PR comments and CI summaries."""
    verb = "would create" if simulated else "created"
    title = "Panopticon pre-merge simulation" if simulated else "Panopticon merge"
    new_conflicts = report["conflicts"]["new"]
    unchanged = report["conflicts"]["unchanged"]
    resolved = report["conflicts"]["resolved"]
    lines = []
    if new_conflicts:
        lines.append(f"⚠️ **{title}: this change {verb} {len(new_conflicts)} interface conflict(s).**")
        lines.append("")
        lines.extend(_format_conflict(c) for c in new_conflicts)
        lines.append("")
        lines.append(
            "Resolve by agreeing canonical names/ownership with the other repo(s) and adding "
            "`panopticon-interface` hints where naming is ambiguous (panopticon-interface-naming skill)."
        )
    else:
        lines.append(f"✅ **{title}: no new interface conflicts.**")
    if resolved:
        lines.append("")
        lines.append(f"Resolves {len(resolved)} existing conflict(s): " + ", ".join(f"`{c['name']}`" for c in resolved))
    if unchanged:
        lines.append("")
        lines.append(f"{len(unchanged)} pre-existing conflict(s) remain: " + ", ".join(f"`{c['name']}`" for c in unchanged))
    changes = []
    for label in ("added", "removed", "changed"):
        if report[label]:
            changes.append(f"{label}: " + ", ".join(f"`{i['name']}` ({i['type']})" for i in report[label]))
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
    # exit 2 distinguishes "new conflicts" from operational errors (1); gating decides blocking
    return 2 if report["conflicts"]["new"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Panopticon shard merge and pre-merge simulation.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("simulate", "dry-run merge report"), ("merge", "replace shard and rebuild")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--local", required=True, help="child repo local index (panopticon/index.json)")
        cmd.add_argument("--repo", required=True, help="child repo name")
        cmd.add_argument("--report-file", help="write the markdown report here")
        cmd.add_argument("--json-report", help="write the raw report JSON here")
        cmd.add_argument("--actions-file", help="write the structured TL;DR actions JSON here")
    sub.choices["simulate"].add_argument("--compiled", required=True, help="instance compiled index")
    sub.choices["merge"].add_argument("--instance-root", required=True, help="instance repo checkout")
    args = parser.parse_args(argv)

    # Same exit-code contract as drift.py/currency.py (pr-evaluation spec: "Checks run
    # independently regardless of earlier failures; gating decides at the end"): an operational
    # failure here must not go unreported, and 0/2 are both already spoken for (clean/conflicts),
    # so any exception here already lands outside those two codes without needing reassignment —
    # this just makes sure it doesn't crash bare with no diagnostic and no report-file written.
    try:
        local_doc = load_index(args.local, kind=KIND_LOCAL, repo=args.repo)
        if args.command == "simulate":
            compiled = load_index(args.compiled, kind=KIND_COMPILED)
            report = simulate_merge(local_doc, compiled, args.repo)
        else:
            report = merge_into_instance(args.instance_root, args.repo, local_doc)
    except IndexValidationError as exc:
        label = "pre-merge simulation" if args.command == "simulate" else "merge"
        print(f"::error::Panopticon {label} could not run: {exc}")
        if args.report_file:
            Path(args.report_file).write_text(format_operational_failure(label, str(exc)) + "\n",
                                               encoding="utf-8")
        return 1
    return _write_report(report, args, simulated=(args.command == "simulate"))


if __name__ == "__main__":
    sys.exit(main())
