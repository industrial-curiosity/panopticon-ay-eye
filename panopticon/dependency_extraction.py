"""Dependency-indexing capability: extraction driver, mirroring panopticon/extraction.py's shape
for a different candidate/schema family (internal library/package dependencies, not interfaces).

Detection layers, most portable first (dependency-indexing capability, "Structural
zero-configuration detection" / "Org-declared registry detection" / "Cross-reference the instance
repo" / "Hint annotations and LLM extraction fallback"):

1. **Structural, zero-config** — a parser that can resolve internality itself from the
   declaration's own shape (e.g. ``go_mod``: a Go module path embeds the org's GitHub identity).
   Such a parser's candidates arrive already resolved; this driver folds them straight in.
2. **Org-declared registry host** — for a candidate a parser could not self-resolve,
   ``dependency_lookup.is_internal_registry`` against the org's ``internal_registries`` config.
3. **Instance cross-reference** — ``dependency_lookup.lookup_registered_producer``: is this name
   already self-registered by some other repo?
4. **Hint / LLM fallback** — a ``panopticon-dependency`` hint pins the name outright; otherwise the
   LLM (locally full-repo, in CI diff-scoped) judges from the panopticon-dependency-extraction
   skill, tagged ``"extracted_by": "llm"``.

No shipped parser today produces layer-2/3-eligible ("ambiguous") candidates — ``go_mod`` fully
resolves internality itself (layer 1) — so ``resolve_candidate_internality`` exists and is tested
independently of any current parser, ready for a future manifest-based parser (npm, Python, JVM)
that cannot self-resolve the way Go's self-describing module paths can.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from .dependencies import KIND_LOCAL, empty_index, save_index, sorted_doc, validate_index
from .dependency_lookup import is_internal_registry, lookup_registered_producer
from .naming import resolve_dependency_name
from .parsers import EXCLUDED_DIRS, iter_files, relative_posix
from .parsers import go_mod
from .skills import load_skill

EXTRACTION_SKILL = "panopticon-dependency-extraction"

DEPENDENCY_REGISTRY = {go_mod.DEPENDENCY_ECOSYSTEM: go_mod}

# File shapes worth showing the LLM when no deterministic parser claimed them — same rationale and
# shape as extraction.py's _FALLBACK_SUFFIXES, plus common manifest lockfiles.
_FALLBACK_SUFFIXES = {
    ".json", ".yaml", ".yml", ".properties", ".toml", ".ini", ".gradle", ".lock",
}
_FALLBACK_MAX_BYTES = 100_000


def detecting_dependency_parsers(repo_root):
    """Registered dependency parsers whose ``detect`` fires for this repo, in registry order."""
    return {
        ecosystem: module
        for ecosystem, module in sorted(DEPENDENCY_REGISTRY.items())
        if module.detect(repo_root)
    }


def run_dependency_parsers(repo_root):
    """Run every detecting dependency parser; returns ``{ecosystem: [candidates]}``."""
    return {
        ecosystem: module.extract(repo_root)
        for ecosystem, module in detecting_dependency_parsers(repo_root).items()
    }


def resolve_candidate_internality(raw_name, resolved_from, org_config, instance=None,
                                   instance_root=None, env=None):
    """Layers 2–3 for a candidate a parser could not self-resolve as internal (layer 1).

    ``resolved_from`` is the host/URL the manifest resolved the dependency from (registry-host
    detection); pass ``None`` when not applicable (e.g. a git-dependency URL is the name itself).
    Returns True/False — never guesses beyond what these two deterministic layers can establish;
    callers fall through to hint/LLM resolution when this returns False.
    """
    if is_internal_registry(resolved_from, org_config.get("internal_registries", [])):
        return True
    owner = lookup_registered_producer(
        raw_name, instance=instance, instance_root=instance_root, env=env
    )
    return owner is not None


def _local_interface_types(repo_root):
    """``{interface_name: type}`` from this repo's own local interface index, or ``{}`` when
    absent/invalid/no ``repo_root`` given — the only internality-cheap, no-network source available
    at extraction time for resolving a ``panopticon-dependency-of`` hint's target type."""
    if repo_root is None:
        return {}
    from .index import KIND_LOCAL as IFACE_KIND_LOCAL
    from .index import IndexValidationError
    from .index import load_index as load_interface_index

    path = Path(repo_root) / "panopticon" / "index.json"
    if not path.is_file():
        return {}
    try:
        iface_doc = load_interface_index(path, kind=IFACE_KIND_LOCAL)
    except IndexValidationError:
        return {}
    return {
        name: entries[0]["type"]
        for name, entries in iface_doc.get("interfaces", {}).items()
        if entries
    }


def dependency_candidates_to_index(candidates, repo_name, repo_root=None):
    """Fold parser/LLM dependency candidates into a schema-valid local dependency index document.

    ``repo_root``, when given, resolves any ``panopticon-dependency-of`` hint into a full
    ``links_to_interface: {name, type}`` by checking this repo's own local interface index; when
    absent or the named interface isn't found there (e.g. owned by a different repo), the link is
    left unset rather than fabricating a type — the dependency entry itself is still recorded.
    """
    doc = empty_index(KIND_LOCAL)
    interface_types = _local_interface_types(repo_root)
    grouped = {}
    for candidate in candidates:
        name = resolve_dependency_name(
            candidate["raw_name"], hint=candidate.get("hint"), source_files=[candidate["source_file"]]
        )
        grouped.setdefault((name, candidate["ecosystem"]), []).append(candidate)
    for (name, ecosystem), group in sorted(grouped.items()):
        owned = [c for c in group if c.get("owned")]
        owner = None
        if owned:
            component = next((c["component"] for c in owned if c.get("component")), None)
            owner = {"repo": repo_name, "component": component}
        entry = {"owner": owner, "ecosystem": ecosystem, "consumer": [], "producer": []}
        for role in ("consumer", "producer"):
            role_candidates = [c for c in group if c["role"] == role]
            files = sorted({c["source_file"] for c in role_candidates})
            if not files:
                continue
            robj = {"repo": repo_name, "source_files": files}
            if role == "consumer":
                apis = sorted({api for c in role_candidates for api in (c.get("apis") or [])})
                if apis:
                    robj["apis"] = apis
            entry[role] = [robj]
        link_hints = {c["links_to_interface_hint"] for c in group if c.get("links_to_interface_hint")}
        if len(link_hints) == 1:
            interface_name = next(iter(link_hints))
            if interface_name in interface_types:
                entry["links_to_interface"] = {"name": interface_name, "type": interface_types[interface_name]}
        if any(c.get("extracted_by") == "llm" for c in group):
            entry["extracted_by"] = "llm"
        doc["dependencies"].setdefault(name, []).append(entry)
    doc = sorted_doc(doc)
    validate_index(doc, kind=KIND_LOCAL, repo=repo_name)
    return doc


def fallback_candidate_files(repo_root, covered_files, changed_files=None):
    """Files the LLM should look at: dependency-shaped, small, uncovered by any parser.

    ``changed_files`` (CI mode) restricts the selection to the PR's diff — full-repo LLM
    extraction happens locally through the user's agent, never in CI.
    """
    repo_root = Path(repo_root)
    covered = set(covered_files)
    changed = set(changed_files) if changed_files is not None else None
    selected = []
    for path in iter_files(repo_root, suffixes=_FALLBACK_SUFFIXES):
        rel = relative_posix(path, repo_root)
        if rel in covered:
            continue
        if changed is not None and rel not in changed:
            continue
        if path.stat().st_size > _FALLBACK_MAX_BYTES:
            continue
        selected.append(rel)
    return selected


def _validate_extraction_response(raw):
    if not isinstance(raw, list):
        raise ValueError("expected a JSON array")
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"item {i} is not a JSON object")
        missing = [f for f in ("raw_name", "ecosystem", "source_file") if f not in item]
        if missing:
            raise ValueError(f"item {i} is missing required field(s): {missing}")


def llm_extract(client, repo_root, candidate_files, skill_root="."):
    """Ask the runtime for dependency candidates in the given files; returns tagged candidates.

    The response contract (panopticon-dependency-extraction skill) is a JSON array of objects with
    raw_name/ecosystem/role/owned/component/source_file/apis/links_to_interface_hint.
    """
    if not candidate_files:
        return []
    repo_root = Path(repo_root)
    sections = []
    for rel in candidate_files:
        text = (repo_root / rel).read_text(encoding="utf-8", errors="replace")
        sections.append(f"### {rel}\n```\n{text}\n```")
    raw = client.complete_json(
        load_skill(EXTRACTION_SKILL, root=skill_root),
        "Identify internal (same-org) dependencies in these files.\n\n" + "\n\n".join(sections),
        _validate_extraction_response,
        response_label="dependency extraction response",
        expected_shape="array",
    )
    candidates = []
    for item in raw:
        candidates.append(
            {
                "raw_name": item["raw_name"],
                "hint": item.get("hint"),
                "ecosystem": item["ecosystem"],
                "role": item.get("role", "consumer"),
                "source_file": item["source_file"],
                "owned": bool(item.get("owned")),
                "component": item.get("component"),
                "apis": item.get("apis"),
                "links_to_interface_hint": item.get("links_to_interface_hint"),
                "extracted_by": "llm",
            }
        )
    return candidates


def parser_gap_recommendations(candidates):
    """One warning per ecosystem that only LLM extraction covered."""
    llm_ecosystems = sorted({c["ecosystem"] for c in candidates if c.get("extracted_by") == "llm"})
    return [
        f"⚠ Dependency ecosystem '{ecosystem}' was extracted by the LLM. Consider contributing a "
        f"deterministic parser for it to the Panopticon template repo (see docs/parser-contribution.md)."
        for ecosystem in llm_ecosystems
    ]


def write_step_summary(lines, env=os.environ):
    """Append lines to the GitHub Actions step summary when running in CI."""
    summary_path = env.get("GITHUB_STEP_SUMMARY")
    if summary_path and lines:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def extract_repo(repo_root, repo_name, client=None, changed_files=None, skill_root="."):
    """Full dependency-extraction pass. Returns (index_doc, summary_lines).

    ``client=None`` runs deterministic parsers only (the local agent harness handles LLM
    judgment itself); passing an ``LLMClient`` enables the CI fallback over ``changed_files``.

    Every registered parser today (``go_mod``) resolves internality itself (detection layer 1,
    module docstring) — no candidate currently needs layers 2/3
    (``resolve_candidate_internality``, org-declared registry / instance cross-reference), so
    they aren't wired in here. That function is independently tested and ready for a future
    manifest-based parser (npm, Python, JVM) that can't self-resolve the way Go can.
    """
    candidates = [c for group in run_dependency_parsers(repo_root).values() for c in group]
    if client is not None:
        covered = {c["source_file"] for c in candidates}
        fallback_files = fallback_candidate_files(repo_root, covered, changed_files)
        candidates.extend(llm_extract(client, repo_root, fallback_files, skill_root=skill_root))
    doc = dependency_candidates_to_index(candidates, repo_name, repo_root=repo_root)
    return doc, parser_gap_recommendations(candidates)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract a repo's local dependency index.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--repo-name", required=True)
    parser.add_argument("--output", help="write the index here (default: stdout)")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="enable the LLM fallback via PANOPTICON_LLM_* (CI only; scoped to --changed-file)",
    )
    parser.add_argument("--changed-file", action="append", default=None, dest="changed_files")
    parser.add_argument("--skill-root", default=".", help="checkout containing .agents/skills")
    args = parser.parse_args(argv)

    client = None
    if args.ci:
        from .llm import LLMClient

        client = LLMClient.from_env()
    doc, summary = extract_repo(
        args.repo_root, args.repo_name, client=client,
        changed_files=args.changed_files, skill_root=args.skill_root,
    )
    if args.output:
        save_index(doc, args.output, kind=KIND_LOCAL, repo=args.repo_name)
    else:
        json.dump(doc, sys.stdout, indent=2, sort_keys=True)
        print()
    for line in summary:
        print(line, file=sys.stderr)
    write_step_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
