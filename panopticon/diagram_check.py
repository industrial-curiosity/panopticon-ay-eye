"""Deterministic diagram-existence PR check (CI only): does the repo's `architecture.md` contain a
well-formed `## Architecture diagram` section in the instance's configured format?

Independent of doc-drift (design D2): this check verifies existence and structure only, never
diagram accuracy — no LLM call, no `PANOPTICON_LLM_*` requirement. It needs the instance repo
checked out first, to read `panopticon.diagram.config.json` via `panopticon.config.load_diagram_config`.
Same exit-code contract as drift.py/currency.py/merge.py: 0=clean, 2=problems found, anything
else=operational failure (never a silent pass).
"""

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_diagram_config, require_supported_diagram_format
from .docs import DIAGRAM_SECTION_HEADING, diagram_section_problems
from .report import format_operational_failure

CHECK_NAME = "diagram-existence"


def format_report(problems):
    """Human-readable report for the PR comment / CI summary."""
    if not problems:
        return "✅ **Panopticon diagram-existence check:** the architecture diagram section is present and well-formed."
    lines = [
        "❌ **Panopticon diagram-existence check: architecture diagram section missing or malformed.**",
        "",
    ]
    lines.extend(f"- {p}" for p in problems)
    lines += [
        "",
        f"How to fix: run the panopticon-doc-generation skill in your agent to add or fix the "
        f"`{DIAGRAM_SECTION_HEADING}` section in `architecture.md`.",
    ]
    return "\n".join(lines)


def collect_actions(problems):
    """Structured remediation actions for the combined-report TL;DR (panopticon/report.py). A
    missing/malformed diagram section collapses into the same `run_doc_generation` action as stale
    docs — running that skill once produces the diagram section in the same pass (pr-evaluation
    spec: "Missing diagram collapses into the same doc-generation action")."""
    if not problems:
        return []
    return [{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic diagram-existence PR check (CI only).")
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--instance-root", default=".",
                        help="checkout to read panopticon.diagram.config.json from")
    parser.add_argument("--report-file", help="write the markdown report here (for PR comments)")
    parser.add_argument("--actions-file", help="write the structured TL;DR actions JSON here")
    args = parser.parse_args(argv)

    try:
        diagram_format = load_diagram_config(args.instance_root)["format"]
        require_supported_diagram_format(diagram_format)
    except ConfigError as exc:
        print(f"::error::Panopticon {CHECK_NAME} check could not run: {exc}")
        if args.report_file:
            Path(args.report_file).write_text(
                format_operational_failure(CHECK_NAME, str(exc)) + "\n", encoding="utf-8"
            )
        return 1

    problems = diagram_section_problems(args.docs_root, diagram_format)
    report = format_report(problems)
    print(report)
    if args.report_file:
        Path(args.report_file).write_text(report + "\n", encoding="utf-8")
    if args.actions_file:
        Path(args.actions_file).write_text(json.dumps(collect_actions(problems)), encoding="utf-8")
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
