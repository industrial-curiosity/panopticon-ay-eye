"""Advisory comparison of a child interface index with the instance index.

Candidate selection is deterministic and bounded. The LLM may explain whether a candidate is a
likely match, likely distinct, or inconclusive, but it never edits a hint/index or decides gating;
``panopticon.merge`` remains the exact prospective-merge authority.
"""

import argparse
import json
from pathlib import Path

from .index import KIND_COMPILED, KIND_LOCAL, load_index
from .llm import (
    LLMClient,
    LLMConfigurationError,
    LLMRequestError,
    LLMResponseError,
    MissingRequirementError,
)
from .report import format_operational_failure
from .skills import load_skill

MATCHING_SKILL = "panopticon-interface-naming"
MATCH_CLASSES = ("likely-same", "likely-distinct", "insufficient-evidence")
MAX_CANDIDATES_PER_CHILD = 5


def _tokens(value):
    return {token for token in str(value).replace("_", "-").split("-") if token}


def select_candidates(local_doc, compiled_doc, max_candidates=MAX_CANDIDATES_PER_CHILD):
    """Select a bounded, deterministic candidate payload for the CI evaluator."""
    instance_entries = [
        (name, entry)
        for name, entries in compiled_doc.get("interfaces", {}).items()
        for entry in entries
    ]
    candidates = []
    for child_name, child_entries in local_doc.get("interfaces", {}).items():
        for child_entry in child_entries:
            scored = []
            for instance_name, instance_entry in instance_entries:
                if instance_entry.get("type") != child_entry.get("type"):
                    continue
                score = 100 if child_name == instance_name else 0
                score += len(_tokens(child_name) & _tokens(instance_name))
                if score:
                    scored.append((score, instance_name, instance_entry))
            scored.sort(key=lambda item: (-item[0], item[1]))
            for score, instance_name, instance_entry in scored[:max_candidates]:
                candidates.append({
                    "child_name": child_name,
                    "instance_name": instance_name,
                    "type": child_entry.get("type"),
                    "score": score,
                    "child_entry": child_entry,
                    "instance_entry": instance_entry,
                })
    return candidates


def _validate_verdict(verdict):
    if not isinstance(verdict, dict):
        raise ValueError("candidate verdict must be an object")
    matches = verdict.get("matches")
    if not isinstance(matches, list):
        raise ValueError("candidate verdict 'matches' must be a list")
    if not isinstance(verdict.get("summary", ""), str):
        raise ValueError("candidate verdict 'summary' must be a string")
    for match in matches:
        if not isinstance(match, dict):
            raise ValueError("each candidate match must be an object")
        for field in ("child_name", "instance_name", "type", "classification", "evidence"):
            if not isinstance(match.get(field), str) or not match[field].strip():
                raise ValueError(f"each candidate match needs a non-empty '{field}'")
        if match["classification"] not in MATCH_CLASSES:
            raise ValueError(f"classification must be one of {list(MATCH_CLASSES)}")


def check_candidates(local_doc, compiled_doc, client, skill_root="."):
    """Run the bounded advisory comparison, or return clean when no candidates exist."""
    candidates = select_candidates(local_doc, compiled_doc)
    if not candidates:
        return {"matches": [], "summary": "No same-type or name-similar instance candidates were found."}
    user_content = (
        "Compare the proposed child interface entries with these bounded instance candidates. "
        "Use source/configuration evidence represented in the entries; do not infer a merge or "
        "edit either index. Return JSON with `matches` (one object per candidate) and `summary`. "
        "Each match must contain child_name, instance_name, type, classification (one of "
        "likely-same, likely-distinct, insufficient-evidence), and concise evidence.\n\n"
        "## Candidates\n```json\n" + json.dumps(candidates, indent=2, sort_keys=True) + "\n```"
    )
    return client.complete_json(
        load_skill(MATCHING_SKILL, root=skill_root),
        user_content,
        _validate_verdict,
        response_label="interface candidate verdict",
    )


def format_report(verdict):
    matches = verdict.get("matches", [])
    if not matches:
        return "✅ **Panopticon interface candidate analysis:** no potential instance matches found."
    lines = [
        "⚠️ **Panopticon interface candidate analysis: review potential organization matches.**",
        "",
        verdict.get("summary", ""),
        "",
        "This is advisory context; deterministic pre-merge simulation remains authoritative.",
        "",
    ]
    for match in matches:
        lines.append(
            f"- `{match['child_name']}` ({match['type']}) ↔ `{match['instance_name']}` — "
            f"**{match['classification']}**: {match['evidence']}"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Advisory child/instance interface comparison.")
    parser.add_argument("--local", required=True)
    parser.add_argument("--compiled", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--skill-root", default=".")
    parser.add_argument("--report-file")
    parser.add_argument("--actions-file")
    args = parser.parse_args(argv)
    try:
        client = LLMClient.from_env()
        local_doc = load_index(args.local, kind=KIND_LOCAL, repo=args.repo)
        compiled_doc = load_index(args.compiled, kind=KIND_COMPILED)
        verdict = check_candidates(local_doc, compiled_doc, client, skill_root=args.skill_root)
    except (MissingRequirementError, LLMConfigurationError, LLMRequestError, LLMResponseError) as exc:
        report = format_operational_failure("interface candidate analysis", str(exc))
        if args.report_file:
            Path(args.report_file).write_text(report + "\n", encoding="utf-8")
        return 1
    report = format_report(verdict)
    print(report)
    if args.report_file:
        Path(args.report_file).write_text(report + "\n", encoding="utf-8")
    if args.actions_file:
        Path(args.actions_file).write_text("[]", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
