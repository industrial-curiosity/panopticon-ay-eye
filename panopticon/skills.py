"""Skill loading: markdown instruction files → system-prompt content.

Skills are the shared contract between the two execution paths (design D5): locally they load
into the user's agent harness; in CI the same files become the system prompt for the stdlib LLM
client. Bundled skills live at ``.agents/skills/<name>/SKILL.md`` relative to the repo root of a
template/instance checkout.

YAML frontmatter is stripped before prompting — it carries harness trigger metadata
(name/description), not instructions.
"""

from pathlib import Path

SKILLS_DIR = Path(".agents") / "skills"


class SkillNotFoundError(Exception):
    def __init__(self, name, path):
        super().__init__(
            f"skill '{name}' not found at {path}. The CI workflow must check out the instance "
            "repo (which bundles the skills) before invoking LLM checks."
        )


def strip_frontmatter(text):
    if not text.startswith("---"):
        return text
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "".join(lines[i + 1 :]).lstrip("\n")
    return text


def skill_path(name, root="."):
    return Path(root) / SKILLS_DIR / name / "SKILL.md"


def load_skill(name, root="."):
    """Return a skill's instruction body (frontmatter stripped) for system-prompt use."""
    path = skill_path(name, root)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SkillNotFoundError(name, path)
    return strip_frontmatter(text)
