"""LLM index-currency check (CI): is the committed local index current for this diff?

Developers keep their repo's local index up to date with their own agents; before the pre-merge
simulation runs, this check verifies they have — a simulation over a stale index would predict
the wrong merge. The CI agent evaluates only what changed in the PR plus the minimal context
required to understand it (never full-repo extraction, which happens locally).

Verdict contract (defined in the panopticon-index-currency skill)::

    {
      "current": false,
      "reasons": [{"what": "...", "index_update": "..."}],
      "summary": "one-line verdict"
    }
"""

import argparse
import json
import sys
from pathlib import Path

from .index import KIND_LOCAL, dumps_index, load_index
from .llm import LLMClient, LLMRequestError, LLMResponseError, MissingRequirementError
from .report import format_operational_failure
from .skills import load_skill

CURRENCY_SKILL = "panopticon-index-currency"


def _validate_currency_verdict(verdict):
    if not isinstance(verdict, dict) or not isinstance(verdict.get("current"), bool):
        raise ValueError("'current' must be a boolean")
    if not isinstance(verdict.get("reasons", []), list):
        raise ValueError("'reasons' must be a list")


def check_currency(diff_text, index_doc, client, skill_root="."):
    """Judge whether the committed local index reflects the diff's interface impact."""
    user_content = (
        "## PR diff\n```diff\n" + diff_text + "\n```\n\n## Committed local index "
        "(panopticon/index.json)\n```json\n" + dumps_index(index_doc) + "```"
    )
    return client.complete_json(
        load_skill(CURRENCY_SKILL, root=skill_root), user_content, _validate_currency_verdict,
        response_label="index-currency verdict",
    )


def format_report(verdict):
    if verdict["current"]:
        return "✅ **Panopticon index-currency check:** the local index is current for this change."
    lines = [
        "❌ **Panopticon index-currency check: `panopticon/index.json` is stale for this change.**",
        "",
        verdict.get("summary", ""),
        "",
    ]
    for reason in verdict.get("reasons", []):
        lines.append(f"- {reason.get('what', '')}")
        if reason.get("index_update"):
            lines.append(f"  - Index update needed: {reason['index_update']}")
    lines += [
        "",
        "Update the index locally with your agent (panopticon-interface-naming and "
        "panopticon-interface-extraction skills), re-render docs, commit, and push.",
    ]
    return "\n".join(lines)


def collect_actions(verdict):
    """Structured remediation actions for the combined-report TL;DR (panopticon/report.py) — the
    same `run_doc_generation` kind drift.py emits for stale docs, so a PR that trips both checks for
    the same underlying index gap gets one TL;DR line, not two."""
    if verdict["current"]:
        return []
    return [{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}]


def main(argv=None):
    parser = argparse.ArgumentParser(description="LLM index-currency check (CI only).")
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--index", default="panopticon/index.json")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--skill-root", default=".")
    parser.add_argument("--report-file", help="write the markdown report here")
    parser.add_argument("--actions-file", help="write the structured TL;DR actions JSON here")
    args = parser.parse_args(argv)

    # Exit-code contract (pr-evaluation spec: "CI checks distinguish operational failure from a
    # business verdict by exit code"): 0=current, 2=stale, anything else=operational failure. Never
    # 1 for a verdict — that's the code an uncaught exception would produce anyway, so a genuine
    # crash must never be mistaken for "the index is stale."
    try:
        client = LLMClient.from_env()
        diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
        index_doc = load_index(args.index, kind=KIND_LOCAL, repo=args.repo)
        verdict = check_currency(diff_text, index_doc, client, skill_root=args.skill_root)
    except (MissingRequirementError, LLMRequestError, LLMResponseError) as exc:
        print(f"::error::Panopticon index-currency check could not run: {exc}")
        # Written to --report-file so the combined report shows this failure (pr-evaluation spec:
        # "Checks run independently...") instead of silently omitting the check that crashed.
        if args.report_file:
            Path(args.report_file).write_text(format_operational_failure("index-currency", str(exc)) + "\n",
                                               encoding="utf-8")
        return 1
    report = format_report(verdict)
    print(report)
    if args.report_file:
        Path(args.report_file).write_text(report + "\n", encoding="utf-8")
    if args.actions_file:
        Path(args.actions_file).write_text(json.dumps(collect_actions(verdict)), encoding="utf-8")
    return 2 if not verdict["current"] else 0


if __name__ == "__main__":
    sys.exit(main())
