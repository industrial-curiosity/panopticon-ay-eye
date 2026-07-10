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

# A check that could not run is never reported as if the PR passed (pr-evaluation spec: "Checks
# run independently... MUST NOT let one check's operational failure make the report imply that
# other checks, or the whole PR, passed") — this line always leads the TL;DR when any check failed
# operationally, whether or not other checks also found real, actionable issues.
FAILURE_NOTICE = (
    "One or more checks could not run — see their sections below for details. This must be "
    "resolved (and the check re-run) before the PR can be evaluated."
)


def dedupe_actions(actions):
    """Collapse to one action per distinct (kind, target) pair, first-seen wins, ordered by
    _ACTION_ORDER regardless of which check(s) contributed each action."""
    seen = {}
    for action in actions:
        key = (action["kind"], action.get("target"))
        seen.setdefault(key, action)
    return sorted(seen.values(), key=lambda a: _ACTION_ORDER.index(a["kind"]))


def render_tldr(actions, has_operational_failure=False):
    """The TL;DR block: a de-duplicated action list, a plain pass statement when there are none, or
    (regardless of actions) a leading failure notice when any check could not run."""
    deduped = dedupe_actions(actions)
    if not deduped and not has_operational_failure:
        return PASS_MESSAGE
    lines = ["**TL;DR — what to do:**", ""]
    if has_operational_failure:
        lines.append(f"- {FAILURE_NOTICE}")
    for action in deduped:
        lines.append(f"- {_TEMPLATES[action['kind']].format(target=action.get('target', ''))}")
    return "\n".join(lines)


def build_combined_report(sections, actions, has_operational_failure=False):
    """``sections``: ordered list of each check's markdown report. ``actions``: combined list of
    action dicts from every check. ``has_operational_failure``: True if any check could not run.
    Returns the full body: TL;DR, per-check detail, TL;DR repeated."""
    tldr = render_tldr(actions, has_operational_failure=has_operational_failure)
    detail = "\n\n---\n\n".join(section for section in sections if section)
    return f"{tldr}\n\n---\n\n{detail}\n\n---\n\n{tldr}\n"


def load_actions(path):
    """Read a JSON actions file written by a check's ``--actions-file``; ``[]`` if absent."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []


def format_operational_failure(check_name, message):
    """Markdown section for a check that could not run (pr-evaluation spec: "Checks run
    independently regardless of earlier failures; gating decides at the end") — distinct from a
    passing or stale verdict, so the combined report never implies the check passed or is silent
    about it. Written to the check's own ``--report-file`` so it flows through the same
    sections-collection path as a normal verdict report — no special-casing needed downstream."""
    return f"⚠️ **Panopticon {check_name} check: could not run.**\n\n{message}"
