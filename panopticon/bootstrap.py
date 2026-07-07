"""Bootstrap installer logic for child-repo initialization.

This module is the implementation behind ``install.py``. All logic is here so it can be
unit-tested as part of the normal test suite.

Invocation from a child repo (no local instance clone required)::

    curl -fsSL https://raw.githubusercontent.com/<instance>/main/install.py | python3

or::

    PANOPTICON_INSTANCE=acme/panopticon-instance python3 install.py

The installer runs three deterministic steps — download skills, wire workflows, check CI
prerequisites — then prints the exact agent prompts that complete initialization.
``panopticon/config.json`` is never written here; it is the last artifact created by the
finalization step after the agent has finished.
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
DEFAULT_WORKFLOW_REF = "v1"
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
    for name in CALLER_WORKFLOWS:
        path = workflows_dir / name
        path.write_text(caller_workflow_text(name, instance, ref, default_branch), encoding="utf-8")
        written.append(path)
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

def download_skills(owner, repo, ref, tree, token=None, child_root=".",
                    urlopen=urllib.request.urlopen):
    """Download panopticon-* skills from the instance tree to the child repo; returns count."""
    blobs = [
        item for item in tree
        if item["type"] == "blob"
        and item["path"].startswith(SKILLS_PREFIX + "panopticon-")
    ]
    if not blobs:
        print("  warning: no panopticon-* skills found under .agents/skills/ in the instance repo")
        return 0
    count = 0
    for item in blobs:
        path = item["path"]
        local = Path(child_root) / path
        local.parent.mkdir(parents=True, exist_ok=True)
        content = _fetch_file_bytes(owner, repo, path, ref, token, urlopen)
        local.write_bytes(content)
        count += 1
    return count

# ── Prerequisite check ────────────────────────────────────────────────────────

def check_prerequisites(org, token=None, urlopen=urllib.request.urlopen):
    """Report-only check of org secrets and variables via the GitHub API. Never blocks."""
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

# ── Agent prompts ─────────────────────────────────────────────────────────────

def agent_prompts(instance):
    """Return the formatted agent prompt block for the given instance slug."""
    return f"""\

╔══════════════════════════════════════════════════════════════════╗
║        Panopticon — complete initialization with your agent     ║
╚══════════════════════════════════════════════════════════════════╝

Give these prompts to your AI agent (Claude Code, Cursor, or any
harness that loads skills from .agents/skills/):

━━━ Prompt 1 — Generate documentation ━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Use the panopticon-doc-generation skill to generate the four
  documentation layers for this repo (architecture overview,
  per-component, interface, and operational docs). Follow the
  skill's instructions exactly and do not skip any layer.

━━━ Prompt 2 — Build the interface index ━━━━━━━━━━━━━━━━━━━━━━━━

  Use the panopticon-interface-naming and
  panopticon-interface-extraction skills to build the local
  interface index at panopticon/index.json. Follow both skills'
  instructions to identify, name, and record all interfaces this
  repo exposes or consumes.

━━━ Prompt 3 — Finalize ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Once prompts 1 and 2 are complete, run the finalization step:

    python3 -m panopticon.init_repo --instance {instance}

  This validates the generated docs and index, then writes
  panopticon/config.json as the final initialization artifact.
  Re-run if anything needs fixing.

Then commit and push:

  git add .github/workflows/ .agents/skills/ docs/ panopticon/
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

    # Read workflow_ref from the instance's org config (fall back to default).
    print(f"\nFetching org config from {instance}...")
    org_config = fetch_org_config(owner, repo, default_branch, token, urlopen)
    ref = org_config.get("workflow_ref", DEFAULT_WORKFLOW_REF)
    print(f"  workflow_ref: {ref}")

    # Download skills.
    print(f"\nDownloading skills from {instance}...")
    try:
        tree = _fetch_tree(owner, repo, default_branch, token, urlopen)
        n_skills = download_skills(owner, repo, default_branch, tree, token, child_root, urlopen)
        print(f"  {n_skills} skill file(s) installed → .agents/skills/")
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
    if issues:
        for issue in issues:
            print(issue)
        print(
            "\n  See the setup guide in the instance repo for configuration instructions.\n"
            "  Missing items will not block initialization — fix before the first PR."
        )
    else:
        print("  All org-level secrets and variables are configured.")

    print(agent_prompts(instance))
    return 0
