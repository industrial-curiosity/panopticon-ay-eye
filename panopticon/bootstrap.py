"""Bootstrap installer logic for child-repo initialization.

This module is the implementation behind ``install.py``. All logic is here so it can be
unit-tested as part of the normal test suite.

Invocation from a child repo (no local instance clone required)::

    curl -fsSL https://raw.githubusercontent.com/<instance>/main/install.py | python3

or::

    PANOPTICON_INSTANCE=acme/panopticon-instance python3 install.py

The installer determines a skills location (prompting for it — even when piped via curl, by
reading from /dev/tty — before downloading anything), then runs the remaining deterministic
steps: download skills to that location, wire workflows, check CI prerequisites, print the exact
agent prompts that complete initialization. ``panopticon/config.json`` is never written here; it
is the last artifact created by the finalization step after the agent has finished.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import SCHEMA_VERSION

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_BRANCH = "main"
SKILLS_PREFIX = ".agents/skills/"
CALLER_WORKFLOWS = ("panopticon-pr.yml", "panopticon-merge.yml", "panopticon-pr-close.yml")
ORG_SECRETS = ("PANOPTICON_LLM_API_KEY", "PANOPTICON_INSTANCE_TOKEN")
ORG_VARS = ("PANOPTICON_LLM_ENDPOINT", "PANOPTICON_LLM_MODEL")

_CALLER_HEADER = (
    "# Wired by Panopticon install.py — a thin reference to the shared workflow in the instance repo.\n"
    "# Re-run install.py to update. Secrets and variables are org-level; this repo configures none.\n"
)

# ── Workflow generation ───────────────────────────────────────────────────────

def caller_workflow_text(name, instance, ref, default_branch=DEFAULT_BRANCH):
    """Return the YAML text for one thin caller workflow."""
    triggers = {
        "panopticon-pr.yml": "on:\n  pull_request:\n",
        "panopticon-merge.yml": f"on:\n  push:\n    branches: [{default_branch}]\n",
        "panopticon-pr-close.yml": "on:\n  pull_request:\n    types: [closed]\n",
    }[name]
    workflow_name = {
        "panopticon-pr.yml": "Panopticon PR checks",
        "panopticon-merge.yml": "Panopticon merge sync",
        "panopticon-pr-close.yml": "Panopticon PR close",
    }[name]
    return (
        f"{_CALLER_HEADER}"
        f"name: {workflow_name}\n"
        f"{triggers}"
        "jobs:\n"
        "  panopticon:\n"
        f"    uses: {instance}/.github/workflows/{name}@{ref}\n"
        "    secrets: inherit\n"
    )


def wire_workflows(instance, ref, child_root=".", default_branch=DEFAULT_BRANCH):
    """Write/refresh the three caller workflows in place; returns their paths."""
    workflows_dir = Path(child_root) / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    written = []
    total = len(CALLER_WORKFLOWS)
    for i, name in enumerate(CALLER_WORKFLOWS, start=1):
        path = workflows_dir / name
        path.write_text(caller_workflow_text(name, instance, ref, default_branch), encoding="utf-8")
        written.append(path)
        print(f"  [{i}/{total}] {name}")
    return written

# ── GitHub API helpers ────────────────────────────────────────────────────────

def _api_headers(token=None):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _api_get(url, token=None, urlopen=urllib.request.urlopen):
    req = urllib.request.Request(url, headers=_api_headers(token))
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        with exc:
            body = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"GitHub API {exc.code} for {url}: {body}")


def _fetch_tree(owner, repo, ref, token=None, urlopen=urllib.request.urlopen):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
    data = _api_get(url, token, urlopen)
    if data.get("truncated"):
        print("  warning: repository tree was truncated; some skills may be missing")
    return data.get("tree", [])


def _fetch_file_bytes(owner, repo, path, ref, token=None, urlopen=urllib.request.urlopen):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    data = _api_get(url, token, urlopen)
    encoding = data.get("encoding", "")
    if encoding == "base64":
        return base64.b64decode(data["content"])
    raise RuntimeError(f"Unexpected file encoding {encoding!r} for {path}")

# ── Token resolution ──────────────────────────────────────────────────────────

def resolve_token(env=None):
    """Return a GitHub API token from env vars or gh CLI auth, or None."""
    env = env if env is not None else os.environ
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        if env.get(key):
            return env[key]
    if shutil.which("gh"):
        try:
            result = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
    return None

# ── Instance slug ─────────────────────────────────────────────────────────────

def resolve_instance(env=None, prompt_fn=None):
    """Return the instance org/repo slug from env or prompt."""
    env = env if env is not None else os.environ
    value = env.get("PANOPTICON_INSTANCE", "").strip()
    if not value:
        if prompt_fn is None:
            if not sys.stdin.isatty():
                sys.exit(
                    "error: PANOPTICON_INSTANCE is not set and stdin is not a terminal.\n"
                    "Set it before piping the installer:\n\n"
                    "    export PANOPTICON_INSTANCE=acme/panopticon-instance\n"
                    "    curl -fsSL https://... | python3"
                )
            prompt_fn = input
        value = prompt_fn(
            "Panopticon instance (owner/repo, e.g. acme/panopticon-instance): "
        ).strip()
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        sys.exit(f"error: PANOPTICON_INSTANCE must be 'owner/repo', got: {value!r}")
    return value

# ── Org config ────────────────────────────────────────────────────────────────

def fetch_org_config(owner, repo, ref, token=None, urlopen=urllib.request.urlopen):
    """Fetch panopticon.config.json from the instance repo; return {} on any error."""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/panopticon.config.json?ref={ref}"
        data = _api_get(url, token, urlopen)
        return json.loads(base64.b64decode(data["content"]))
    except Exception:
        return {}

# ── Skills download ───────────────────────────────────────────────────────────

def download_skills(owner, repo, ref, tree, token=None, child_root=".", dest_location=None,
                    urlopen=urllib.request.urlopen):
    """Download panopticon-* skills from the instance tree to `dest_location` in the child repo
    (defaults to `.agents/skills`); returns count. The instance repo always stores skills under
    `.agents/skills/` (SKILLS_PREFIX) — only the child-repo destination varies."""
    dest_location = dest_location if dest_location is not None else DEFAULT_SKILLS_LOCATION
    blobs = [
        item for item in tree
        if item["type"] == "blob"
        and item["path"].startswith(SKILLS_PREFIX + "panopticon-")
    ]
    if not blobs:
        print("  warning: no panopticon-* skills found under .agents/skills/ in the instance repo")
        return 0
    total = len(blobs)
    count = 0
    for item in blobs:
        path = item["path"]
        relative = path[len(SKILLS_PREFIX):]
        local = Path(child_root) / dest_location / relative
        local.parent.mkdir(parents=True, exist_ok=True)
        content = _fetch_file_bytes(owner, repo, path, ref, token, urlopen)
        local.write_bytes(content)
        count += 1
        print(f"  [{count}/{total}] {relative}")
    return count

# ── Local tooling vendoring ─────────────────────────────────────────────────────
# The exact transitive import closure of `python3 -m panopticon.init_repo` and the
# `python3 -m panopticon.docs` commands panopticon-doc-generation/SKILL.md invokes directly —
# confirmed by reading each module's imports. All stdlib-only. Everything else in panopticon/
# (llm.py, drift.py, currency.py, merge.py, extraction.py, skills.py, bootstrap.py, parsers/) is
# used only by the reusable GitHub Actions workflows that check out the instance repo directly,
# and has no role in local Phase 2/3 work — it SHALL NOT be vendored into child repos.
LOCAL_TOOLING_MODULES = ("__init__.py", "config.py", "docs.py", "index.py", "init_repo.py")


def download_local_tooling(owner, repo, ref, token=None, child_root=".",
                           urlopen=urllib.request.urlopen):
    """Vendor LOCAL_TOOLING_MODULES into the child repo's panopticon/ directory, so
    `python3 -m panopticon.docs` / `python3 -m panopticon.init_repo` work immediately after
    bootstrap with no instance-repo clone or PYTHONPATH setup. Idempotent: overwrites in place."""
    dest_dir = Path(child_root) / "panopticon"
    dest_dir.mkdir(parents=True, exist_ok=True)
    total = len(LOCAL_TOOLING_MODULES)
    for i, name in enumerate(LOCAL_TOOLING_MODULES, start=1):
        content = _fetch_file_bytes(owner, repo, f"panopticon/{name}", ref, token, urlopen)
        (dest_dir / name).write_bytes(content)
        print(f"  [{i}/{total}] {name}")
    return total

# ── Prerequisite check ────────────────────────────────────────────────────────

def manual_verification_steps(org):
    """Printable steps for verifying org secrets/variables by hand when no token is available.

    The org secrets/variables API requires an admin-scoped token; without one there is no way
    to query it automatically, so this is not a failure — it's the fallback path.
    """
    settings_url = f"https://github.com/organizations/{org}/settings/secrets/actions"
    return [
        "  no GitHub auth token found (GH_TOKEN / GITHUB_TOKEN / gh auth) — org secrets and "
        "variables can't be checked automatically. Verify manually that these are configured:",
        f"    secrets:   {', '.join(ORG_SECRETS)}",
        f"    variables: {', '.join(ORG_VARS)}",
        "",
        "  Web UI:",
        f"    {settings_url}",
        "    (secrets and variables are separate tabs on that page)",
        "",
        "  Or locally via the gh CLI (run `gh auth login` first if not already authenticated):",
        f"    gh secret list --org {org}",
        f"    gh variable list --org {org}",
    ]


def check_prerequisites(org, token=None, urlopen=urllib.request.urlopen):
    """Report-only check of org secrets and variables via the GitHub API. Never blocks.

    Without a token there is nothing to query — see ``manual_verification_steps``.
    """
    if not token:
        return manual_verification_steps(org)

    report = []
    settings_url = f"https://github.com/organizations/{org}/settings/secrets/actions"

    def _check(endpoint, collection_key, items, kind):
        try:
            url = f"https://api.github.com/orgs/{org}/actions/{endpoint}"
            data = _api_get(url, token, urlopen)
            existing = {item["name"] for item in data.get(collection_key, [])}
            for name in items:
                if name not in existing:
                    report.append(
                        f"  missing org-level {kind}: {name}\n"
                        f"  → configure at {settings_url}"
                    )
        except RuntimeError as exc:
            report.append(f"  could not verify org {kind}s: {exc} — verify manually.")

    _check("secrets", "secrets", ORG_SECRETS, "secret")
    _check("variables", "variables", ORG_VARS, "variable")
    return report

# ── Skills location selection ───────────────────────────────────────────────────
# The bootstrap script prompts for the skills location itself — even when piped via
# `curl | python3` — by reading from /dev/tty directly, since piped stdin is consumed by the
# script content rather than connected to a terminal. No separate script or manual step.
DEFAULT_SKILLS_LOCATION = ".agents/skills"

# Project/workspace-level tool support — mirrors the table in docs/agentskills-support.md, which
# is the source of truth; keep this constant in sync with that doc. Maps tool id -> (display
# name, tuple of locations it reads skills from).
TOOL_LOCATIONS = {
    "vscode": ("VS Code (GitHub Copilot)", (".agents/skills", ".github/skills", ".claude/skills")),
    "visual-studio": ("Visual Studio 2026", (".agents/skills", ".github/skills", ".claude/skills")),
    "cursor": ("Cursor", (".agents/skills", ".cursor/skills")),
    "jetbrains": ("JetBrains IDEs (AI Assistant)", (".agents/skills", ".claude/skills", ".codex/skills")),
    "claude-code": ("Claude Code", (".claude/skills",)),
    "google-antigravity": ("Google Antigravity", (".agents/skills",)),
    "openai-codex": ("OpenAI Codex", (".agents/skills",)),
    "opencode": ("opencode", (".agents/skills", ".opencode/skills", ".claude/skills")),
    "pi": ("Pi", (".agents/skills", ".pi/skills")),
}


def candidate_locations():
    """Return the ordered, de-duplicated union of every location any TOOL_LOCATIONS tool reads,
    with the default (.agents/skills) always first."""
    locations = [DEFAULT_SKILLS_LOCATION]
    for _, tool_locations in TOOL_LOCATIONS.values():
        for loc in tool_locations:
            if loc not in locations:
                locations.append(loc)
    return locations


def compatibility_table_lines():
    """Printable lines listing each tool and the location(s) it reads skills from."""
    lines = ["  Which tools read skills from which location (docs/agentskills-support.md):"]
    for name, tool_locations in TOOL_LOCATIONS.values():
        lines.append(f"    {name}: {', '.join(tool_locations)}")
    return lines


def _detect_existing_location(child_root="."):
    """Return the candidate location that already contains installed panopticon-* skills from a
    prior run, or None if none do."""
    for loc in candidate_locations():
        d = Path(child_root) / loc
        if d.is_dir() and any(p.name.startswith("panopticon-") for p in d.iterdir()):
            return loc
    return None


def _resolve_typed_answer(answer, locations):
    """Interpret a typed prompt answer: blank -> default, a number -> that list index, anything
    else -> treated as a literal path."""
    answer = answer.strip()
    if not answer:
        return locations[0]
    if answer.isdigit():
        index = int(answer) - 1
        if 0 <= index < len(locations):
            return locations[index]
        return locations[0]
    return answer.strip("/")


def _apply_key(selected, count, key):
    """Pure state transition for the arrow-key menu: given the currently selected index and a
    raw key read from the terminal (a single byte, or the 3-byte ESC sequence for an arrow key),
    return (new_selected, done)."""
    if key in (b"\r", b"\n"):
        return selected, True
    if key == b"\x1b[A":
        return (selected - 1) % count, False
    if key == b"\x1b[B":
        return (selected + 1) % count, False
    return selected, False


def _write_menu(fd, locations, selected, first_draw=False):
    lines = []
    if not first_draw:
        lines.append(f"\x1b[{len(locations) + 1}A".encode())
    lines.append(b"\x1b[2K\rUse up/down arrows and enter to choose a skills location:\r\n")
    for i, loc in enumerate(locations):
        marker = b"> " if i == selected else b"  "
        lines.append(b"\x1b[2K" + marker + loc.encode() + b"\r\n")
    os.write(fd, b"".join(lines))


def _arrow_key_menu(locations, default_index=0, tty_path="/dev/tty"):
    """Render an arrow-key selection menu on `tty_path` using raw terminal mode. Returns the
    chosen index, or None if raw terminal interaction isn't available (caller falls back to a
    typed prompt) — e.g. no `termios`/`tty` module (non-POSIX), or `tty_path` can't be opened."""
    try:
        import termios
        import tty as tty_module
    except ImportError:
        return None
    try:
        fd = os.open(tty_path, os.O_RDWR)
    except OSError:
        return None

    try:
        old_settings = termios.tcgetattr(fd)
    except termios.error:
        os.close(fd)
        return None

    selected = default_index
    try:
        tty_module.setraw(fd)
        _write_menu(fd, locations, selected, first_draw=True)
        while True:
            key = os.read(fd, 1)
            if key == b"\x1b":
                key += os.read(fd, 2)
            selected, done = _apply_key(selected, len(locations), key)
            _write_menu(fd, locations, selected)
            if done:
                break
    finally:
        # TCSANOW, not TCSADRAIN: draining waits for the pty's other end to consume pending
        # output, which can hang if nothing is reading it (observed in tests using a pty pair
        # with no reader on the master side). Restoring settings doesn't need to wait for that.
        termios.tcsetattr(fd, termios.TCSANOW, old_settings)
        os.close(fd)
    return selected


def _tty_typed_prompt(prompt_text, tty_path="/dev/tty"):
    """Write `prompt_text` and read one line from `tty_path`. Returns the typed string, or None
    if the tty can't be opened."""
    try:
        tty_read = open(tty_path, "r")
        tty_write = open(tty_path, "w")
    except OSError:
        return None
    try:
        tty_write.write(prompt_text)
        tty_write.flush()
        line = tty_read.readline()
    finally:
        tty_read.close()
        tty_write.close()
    return line.rstrip("\n")


def select_skills_location(env=None, prompt_fn=None, child_root="."):
    """Return the skills location to install to. Never blocks.

    Precedence: `PANOPTICON_SKILLS_LOCATION` env var, a location already populated by a prior run
    (idempotent re-run), an interactive prompt (arrow-key menu on /dev/tty, falling back to a
    typed prompt there, falling back to plain `input()` if stdin is itself a terminal), then the
    `.agents/skills` default when no interactive input is available at all.
    """
    env = env if env is not None else os.environ
    override = env.get("PANOPTICON_SKILLS_LOCATION", "").strip()
    if override:
        return override.strip("/")

    existing = _detect_existing_location(child_root)
    if existing:
        return existing

    locations = candidate_locations()
    for line in compatibility_table_lines():
        print(line)
    prompt_text = f"  Choose a skills location [1-{len(locations)}] or path (default {locations[0]}): "

    if prompt_fn is not None:
        return _resolve_typed_answer(prompt_fn(prompt_text), locations)

    index = _arrow_key_menu(locations, default_index=0)
    if index is not None:
        return locations[index]

    typed = _tty_typed_prompt(prompt_text)
    if typed is not None:
        return _resolve_typed_answer(typed, locations)

    if sys.stdin.isatty():
        return _resolve_typed_answer(input(prompt_text), locations)

    return locations[0]


# ── Agent prompts ─────────────────────────────────────────────────────────────

def agent_prompts():
    """Return the formatted agent prompt block: a single /panopticon-init invocation."""
    return """\

╔══════════════════════════════════════════════════════════════════╗
║        Panopticon — complete initialization with your agent     ║
╚══════════════════════════════════════════════════════════════════╝

Give this prompt to your AI agent (Claude Code, Cursor, or whichever
tool you use — it reads skills from wherever you just installed them):

  /panopticon-init

This runs interface naming, interface extraction, documentation
generation, and finalization in order, resuming from where it left
off if interrupted. Each step remains invocable on its own by name
if you'd rather run just one.

Then commit and push:

  git add -A
  git commit -m "chore: initialize Panopticon"
  git push
"""

# ── Main ──────────────────────────────────────────────────────────────────────

def main(env=None, child_root=".", prompt_fn=None, urlopen=urllib.request.urlopen):
    """Run the bootstrap installer. Returns 0 on success, 1 on error."""
    env = env if env is not None else os.environ
    print("Panopticon bootstrap installer\n")

    instance = resolve_instance(env, prompt_fn)
    owner, repo = instance.split("/")
    print(f"Instance: {instance}")

    token = resolve_token(env)
    if not token:
        print(
            "  warning: no GitHub token found (GH_TOKEN / GITHUB_TOKEN / gh auth).\n"
            "  Private instance repos require a token. Set GH_TOKEN and re-run if this fails."
        )

    default_branch = env.get("PANOPTICON_DEFAULT_BRANCH", DEFAULT_BRANCH)

    # Read workflow_ref from the instance's org config. No manual tagging is required to get
    # started: when the org hasn't set workflow_ref, caller workflows pin to the instance repo's
    # default branch rather than a git tag (org owners can opt into a pinned tag/branch later).
    print(f"\nFetching org config from {instance}...")
    org_config = fetch_org_config(owner, repo, default_branch, token, urlopen)
    ref = org_config.get("workflow_ref", default_branch)
    print(f"  workflow_ref: {ref}")

    # Determine the skills location before downloading anything — prompts even when piped, by
    # reading from /dev/tty (see select_skills_location).
    print()
    location = select_skills_location(env, prompt_fn, child_root)
    print(f"  skills location: {location}")

    # Download skills.
    print(f"\nDownloading skills from {instance}...")
    try:
        tree = _fetch_tree(owner, repo, default_branch, token, urlopen)
        n_skills = download_skills(owner, repo, default_branch, tree, token, child_root,
                                   location, urlopen)
        print(f"  {n_skills} skill file(s) installed → {location}/")
    except RuntimeError as exc:
        print(f"  error: {exc}")
        return 1

    # Vendor the local-tooling subset of panopticon/ (python3 -m panopticon.docs and
    # panopticon.init_repo need this to work with no instance-repo clone or PYTHONPATH setup).
    print("\nVendoring local Python tooling...")
    try:
        n_modules = download_local_tooling(owner, repo, default_branch, token, child_root, urlopen)
        print(f"  {n_modules} module(s) installed → panopticon/")
    except RuntimeError as exc:
        print(f"  error: {exc}")
        return 1

    # Wire workflows.
    print("\nWiring GitHub Actions workflows...")
    wire_workflows(instance, ref, child_root, default_branch)
    print(f"  {len(CALLER_WORKFLOWS)} workflow(s) written → .github/workflows/")

    # Check prerequisites (report-only, never blocks).
    print("\nChecking org CI prerequisites (report-only)...")
    issues = check_prerequisites(owner, token, urlopen)
    if not token:
        for issue in issues:
            print(issue)
    elif issues:
        for issue in issues:
            print(issue)
        print(
            "\n  See the setup guide in the instance repo for configuration instructions.\n"
            "  Missing items will not block initialization — fix before the first PR."
        )
    else:
        print("  All org-level secrets and variables are configured.")

    print(agent_prompts())
    return 0
