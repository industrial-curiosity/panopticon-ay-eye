# Agent Skills (SKILL.md) discovery paths across AI tools and IDEs

Where AI tools and IDEs look for the [Agent Skills](https://agentskills.io) open standard
(`SKILL.md`) is fragmented. `.agents/skills/` is emerging as the tool-agnostic community
default, but adoption is split between that generic folder, platform-specific dotfiles, and
legacy directories. This is the compatibility breakdown as of 2026-07-09, verified against each
tool's own documentation (see [Sources](#sources)).

## Project / workspace-level discovery

Paths are relative to the workspace or repo root.

| Tool | Supports `.agents/skills/`? | Also discovers | Notes |
| --- | --- | --- | --- |
| VS Code (GitHub Copilot) | Yes | `.github/skills/`, `.claude/skills/` | Custom paths can be forced with the `chat.agentSkillsLocations` setting. |
| Visual Studio 2026 | Yes | `.github/skills/`, `.claude/skills/` | Auto-discovers all three layout variants at the solution root. |
| Cursor | Yes | `.cursor/skills/` (legacy) | `.agents/skills/` is the current path; `.cursor/skills/` still works for older setups. |
| JetBrains IDEs (AI Assistant) | Yes | `.claude/skills/`, `.codex/skills/` | Detects skills in the legacy folders and offers to import them. |
| Claude Code | **No** | `.claude/skills/` only | Does not read `.agents/skills/` at all — confirmed directly against Claude Code's own docs, which mention no `.agents/` path anywhere. |
| Google Antigravity | Yes | — | Reads the plural `.agents/skills/` at workspace level. No primary source supports a preference for a singular `.agent/skills/` variant (see [Corrections](#corrections-from-the-original-draft)). |
| OpenAI Codex | Yes | — | Repo-level: `$CWD/.agents/skills` and `$REPO_ROOT/.agents/skills` (see [Corrections](#corrections-from-the-original-draft)). |
| opencode | Yes | `.opencode/skills/`, `.claude/skills/` | Natively supports all three locations in parallel, walking up from cwd to the git worktree root. |
| Pi (Earendil Inc.) | Yes | `.pi/skills/` | Searches cwd and ancestor directories; loose root-level `.md` files in `.pi/skills/` are also discovered as individual skills, not just `SKILL.md` in subfolders. |

## Global / user-profile-level discovery

Paths live under the home directory (`~`).

- **The agnostic standard (`~/.agents/skills/`)** — natively read by VS Code, Visual Studio,
  JetBrains, Cursor, OpenAI Codex (as `$HOME/.agents/skills`), opencode, and Pi.
- **The outliers:**
  - **Claude Code** — strictly `~/.claude/skills/`; does not check `~/.agents/`.
  - **Google Antigravity** — `~/.gemini/config/skills/` (or `~/.gemini/skills/`); does not check
    `~/.agents/` out of the box.
- Visual Studio additionally reads `~/.copilot/skills/` and `~/.claude/skills/` alongside
  `~/.agents/skills/` at the global level. opencode additionally reads
  `~/.config/opencode/skills/` and `~/.claude/skills/`; Pi additionally reads
  `~/.pi/agent/skills/`.

## Corrections from the original draft

Two claims in the earlier version of this doc didn't hold up against current official sources:

- **OpenAI Codex** was listed as an outlier expecting `~/.codex/skills/`. Per OpenAI's current
  official docs, Codex actually follows the agnostic `.agents/skills/` standard at both repo and
  user level (`$HOME/.agents/skills`). Several older third-party posts still describe
  `~/.codex/skills/`, but that's outdated relative to the current docs.
- **Google Antigravity**'s claimed preference for a singular `.agent/skills/` folder at the
  workspace level isn't supported by primary sources; the documented/canonical path is plural
  `.agents/skills/`.

## What this means for this repo

Panopticon's bootstrap script asks where to install skills before downloading anything, defaulting to
`.agents/skills/` (per the `repo-initialization` spec) so they're discoverable by the agnostic-standard
tools above without extra setup. **Claude Code is the one tool in this table that won't pick them up from
`.agents/skills/`.**

If Claude Code is the only tool you need, select `.claude/skills` at the prompt (`docs/setup-guide.md`,
Phase 1). None of this table's "also discovers" locations cover both Claude Code and an
`.agents/skills/`-native tool at once, so supporting both means either running the installer twice at two
different locations or manually symlinking one to the other afterward
(`ln -s .agents/skills .claude/skills`) — Claude Code needs a session restart afterward since it only
watches directories that existed at session start.

## Sources

- [Use Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [Agent Skills in Visual Studio](https://devblogs.microsoft.com/visualstudio/agent-skills-in-visual-studio/)
- [Agent Skills | Cursor Docs](https://cursor.com/docs/skills)
- [Skills | JetBrains AI Assistant Documentation](https://www.jetbrains.com/help/ai-assistant/agent-skills.html)
- [Extend Claude with skills | Claude Code Docs](https://code.claude.com/docs/en/skills.md)
- [Where does Antigravity look for Agent Skills?](https://medium.com/google-cloud/where-does-antigravity-look-for-agent-skills-a703518d68c5)
- [Authoring Google Antigravity Skills](https://codelabs.developers.google.com/getting-started-with-antigravity-skills)
- [Agent Skills – Codex | OpenAI Developers](https://developers.openai.com/codex/skills)
- [Skills | opencode Docs](https://opencode.ai/docs/skills/)
- [Skills | Pi Docs](https://pi.dev/docs/latest/skills)
