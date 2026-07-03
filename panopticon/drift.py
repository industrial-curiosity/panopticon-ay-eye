"""LLM doc-vs-code drift check (CI): diff + docs in, verdict + reasons out.

Developers keep docs current locally with their own agents; this check verifies they have. The
verdict contract (defined in the panopticon-doc-drift skill) is JSON::

    {
      "stale": true,
      "reasons": [{"doc": "docs/components/api.md", "why": "...", "update": "..."}],
      "summary": "one-line verdict"
    }

A stale verdict fails loudly with remediation guidance; whether that fails the workflow is org
gating configuration (read by the workflow, not decided here). Malformed responses and missing
requirements are loud errors — never a silent pass (agent-runtime spec).
"""

import argparse
import json
import sys
from pathlib import Path

from .llm import LLMClient, LLMResponseError
from .skills import load_skill

DRIFT_SKILL = "panopticon-doc-drift"
MAX_DOC_BYTES = 200_000


def check_drift(diff_text, docs, client, skill_root="."):
    """Judge whether the docs require updates for this diff. ``docs`` is ``{path: text}``."""
    doc_sections = [f"### {path}\n```markdown\n{text}\n```" for path, text in sorted(docs.items())]
    user_content = (
        "## PR diff\n```diff\n" + diff_text + "\n```\n\n## Current documentation\n\n"
        + "\n\n".join(doc_sections)
    )
    response = client.complete_with_skill(load_skill(DRIFT_SKILL, root=skill_root), user_content)
    try:
        verdict = json.loads(_strip_code_fence(response))
        stale = verdict["stale"]
        reasons = verdict.get("reasons", [])
        if not isinstance(stale, bool) or not isinstance(reasons, list):
            raise ValueError("bad field types")
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise LLMResponseError(
            f"drift verdict is not the expected JSON shape ({exc}): {response[:500]!r}"
        )
    return verdict


def _strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[-1].strip().startswith("```"):
            return "\n".join(lines[1:-1])
    return text


def format_report(verdict):
    """Human-readable report for the PR comment / CI summary."""
    if not verdict["stale"]:
        return "✅ **Panopticon doc-drift check:** docs are consistent with this change."
    lines = [
        "❌ **Panopticon doc-drift check: documentation updates required.**",
        "",
        verdict.get("summary", ""),
        "",
    ]
    for reason in verdict.get("reasons", []):
        lines.append(f"- **{reason.get('doc', 'docs')}** — {reason.get('why', '')}")
        if reason.get("update"):
            lines.append(f"  - What to update: {reason['update']}")
    lines += [
        "",
        "Update the docs locally with your agent (panopticon-doc-generation skill), commit, and push.",
    ]
    return "\n".join(line for line in lines if line is not None)


def collect_docs(docs_root):
    docs_root = Path(docs_root)
    docs = {}
    budget = MAX_DOC_BYTES
    for path in sorted(docs_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        budget -= len(text)
        if budget < 0:
            break
        docs[path.relative_to(docs_root.parent).as_posix()] = text
    return docs


def main(argv=None):
    parser = argparse.ArgumentParser(description="LLM doc-vs-code drift check (CI only).")
    parser.add_argument("--diff-file", required=True, help="file containing the PR diff")
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--skill-root", default=".", help="checkout containing .agents/skills")
    parser.add_argument("--report-file", help="write the markdown report here (for PR comments)")
    args = parser.parse_args(argv)

    client = LLMClient.from_env()
    diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
    verdict = check_drift(diff_text, collect_docs(args.docs_root), client, skill_root=args.skill_root)
    report = format_report(verdict)
    print(report)
    if args.report_file:
        Path(args.report_file).write_text(report + "\n", encoding="utf-8")
    return 1 if verdict["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
