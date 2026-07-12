"""Extraction driver: deterministic parsers first, LLM fallback for the rest.

Runs every detecting parser (``panopticon.parsers``), canonicalizes candidate names (hints first,
then normalization rules — ``panopticon.naming``), and folds candidates into a local index
document. Files that no deterministic parser touched become LLM-fallback candidates:

- **locally** the user's agent harness judges them with the panopticon-interface-extraction
  skill (full-repo work happens locally, never in CI);
- **in CI** the agent runtime evaluates only the changed files plus minimal context, and the
  resulting names must still resolve from hints and normalization rules — LLM naming judgment is
  local-only (design D9), so an unresolvable name raises ``UnresolvableNameError`` telling the
  developer to add a hint.

LLM-extracted entries are tagged ``"extracted_by": "llm"`` and each such interface type produces
a parser-gap recommendation for the workflow summary.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from .index import KIND_LOCAL, empty_index, save_index, sorted_doc, validate_index
from .naming import resolve_name
from .parsers import EXCLUDED_DIRS, iter_files, relative_posix, run_parsers
from .skills import load_skill

EXTRACTION_SKILL = "panopticon-interface-extraction"

# File shapes worth showing the LLM when no deterministic parser claimed them.
_FALLBACK_SUFFIXES = {".json", ".yaml", ".yml", ".properties", ".toml", ".ini", ".proto", ".graphql"}
_FALLBACK_MAX_BYTES = 100_000


def candidates_to_index(candidates, repo_name):
    """Fold parser/LLM candidates into a schema-valid local index document."""
    doc = empty_index(KIND_LOCAL)
    grouped = {}
    for candidate in candidates:
        name = resolve_name(
            candidate["raw_name"], hint=candidate.get("hint"), source_files=[candidate["source_file"]]
        )
        grouped.setdefault((name, candidate["type"]), []).append(candidate)
    for (name, iface_type), group in sorted(grouped.items()):
        owned = [c for c in group if c.get("owned")]
        owner = None
        if owned:
            component = next((c["component"] for c in owned if c.get("component")), None)
            owner = {"repo": repo_name, "component": component or repo_name}
        entry = {"owner": owner, "type": iface_type, "consumer": [], "producer": []}
        for role in ("consumer", "producer"):
            files = sorted({c["source_file"] for c in group if c["role"] == role})
            if files:
                entry[role] = [{"repo": repo_name, "source_files": files}]
        if any(c.get("extracted_by") == "llm" for c in group):
            entry["extracted_by"] = "llm"
        doc["interfaces"].setdefault(name, []).append(entry)
    doc = sorted_doc(doc)
    validate_index(doc, kind=KIND_LOCAL, repo=repo_name)
    return doc


def fallback_candidate_files(repo_root, covered_files, changed_files=None):
    """Files the LLM should look at: interface-shaped, small, uncovered by any parser.

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
        missing = [f for f in ("raw_name", "type", "source_file") if f not in item]
        if missing:
            raise ValueError(f"item {i} is missing required field(s): {missing}")


def llm_extract(client, repo_root, candidate_files, skill_root="."):
    """Ask the runtime for interface candidates in the given files; returns tagged candidates.

    The response contract (defined in the panopticon-interface-extraction skill) is a JSON array
    of objects with raw_name/type/role/owned/component/source_file.
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
        "Identify service interfaces in these files.\n\n" + "\n\n".join(sections),
        _validate_extraction_response,
        response_label="extraction response",
        expected_shape="array",
    )
    candidates = []
    for item in raw:
        candidates.append(
            {
                "raw_name": item["raw_name"],
                "hint": item.get("hint"),
                "type": item["type"],
                "role": item.get("role", "consumer"),
                "source_file": item["source_file"],
                "owned": bool(item.get("owned")),
                "component": item.get("component"),
                "extracted_by": "llm",
            }
        )
    return candidates


def parser_gap_recommendations(candidates):
    """One warning per interface type that only LLM extraction covered."""
    llm_types = sorted({c["type"] for c in candidates if c.get("extracted_by") == "llm"})
    return [
        f"⚠ Interface type '{iface_type}' was extracted by the LLM. Consider contributing a "
        f"deterministic parser for it to the Panopticon template repo (see docs/parser-contribution.md)."
        for iface_type in llm_types
    ]


def write_step_summary(lines, env=os.environ):
    """Append lines to the GitHub Actions step summary when running in CI."""
    summary_path = env.get("GITHUB_STEP_SUMMARY")
    if summary_path and lines:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def extract_repo(repo_root, repo_name, client=None, changed_files=None, skill_root="."):
    """Full extraction pass. Returns (index_doc, summary_lines).

    ``client=None`` runs deterministic parsers only (the local agent harness handles LLM
    judgment itself); passing an ``LLMClient`` enables the CI fallback over ``changed_files``.
    """
    candidates = [c for group in run_parsers(repo_root).values() for c in group]
    if client is not None:
        covered = {c["source_file"] for c in candidates}
        fallback_files = fallback_candidate_files(repo_root, covered, changed_files)
        candidates.extend(llm_extract(client, repo_root, fallback_files, skill_root=skill_root))
    return candidates_to_index(candidates, repo_name), parser_gap_recommendations(candidates)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract a repo's local interface index.")
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
