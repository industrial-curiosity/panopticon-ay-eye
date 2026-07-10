"""Combined PR-evaluation report: a de-duplicated TL;DR built from every check's structured
actions, shown before and after the per-check detail (pr-evaluation spec: "Combined report leads
with a de-duplicated action list").

Each check (drift.py, currency.py, merge.py) exposes its own ``collect_actions(...)`` returning a
list of ``{"kind": ..., "target": ...}`` dicts describing concrete remediation steps — never free
prose. Doc-drift and index-currency findings both emit the same ``run_doc_generation`` kind
(no ``target`` — it always means "run the whole skill once"), since panopticon-doc-generation's own
rules already keep the index current before regenerating every stale doc in one pass; de-duplication
collapses any number of these into the single line, never one line per stale doc or a separate index
line. De-duplication itself is exact dict-key matching on ``(kind, target)``, not text similarity.
"""

import json
from pathlib import Path

# Fixed section order for the TL;DR, independent of which check emitted which action or the order
# actions were collected in.
_ACTION_ORDER = ("run_doc_generation", "resolve_conflict", "commit_and_push")

_TEMPLATES = {
    "run_doc_generation": (
        "Run the panopticon-doc-generation skill in your agent once — it keeps `panopticon/index.json` "
        "current and regenerates every stale doc (including re-rendering `interfaces.md`) in the same pass."
    ),
    "resolve_conflict": (
        "Resolve the `{target}` interface conflict — agree canonical naming/ownership with the "
        "other repo(s) and add a `panopticon-interface` hint if naming is ambiguous."
    ),
    "commit_and_push": "Commit the fix and push it to this same PR's branch — do not open a new PR.",
}

PASS_MESSAGE = "**TL;DR: all Panopticon checks passed.** No action needed."


def dedupe_actions(actions):
    """Collapse to one action per distinct (kind, target) pair, first-seen wins, ordered by
    _ACTION_ORDER regardless of which check(s) contributed each action."""
    seen = {}
    for action in actions:
        key = (action["kind"], action.get("target"))
        seen.setdefault(key, action)
    return sorted(seen.values(), key=lambda a: _ACTION_ORDER.index(a["kind"]))


def render_tldr(actions):
    """The TL;DR block: a de-duplicated action list, or a plain pass statement when there are none."""
    deduped = dedupe_actions(actions)
    if not deduped:
        return PASS_MESSAGE
    lines = ["**TL;DR — what to do:**", ""]
    for action in deduped:
        lines.append(f"- {_TEMPLATES[action['kind']].format(target=action.get('target', ''))}")
    return "\n".join(lines)


def build_combined_report(sections, actions):
    """``sections``: ordered list of each check's markdown report. ``actions``: combined list of
    action dicts from every check. Returns the full body: TL;DR, per-check detail, TL;DR repeated."""
    tldr = render_tldr(actions)
    detail = "\n\n---\n\n".join(section for section in sections if section)
    return f"{tldr}\n\n---\n\n{detail}\n\n---\n\n{tldr}\n"


def load_actions(path):
    """Read a JSON actions file written by a check's ``--actions-file``; ``[]`` if absent."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
