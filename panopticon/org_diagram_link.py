"""Org-diagram link script (architecture-diagrams capability: "Org-diagram link script"): prints a
resolvable, clickable GitHub URL to this repo's section of the org-wide architecture diagram.

Complements the relative link embedded in this repo's own `## Architecture diagram` section
(panopticon-doc-generation): that embedded link is authored for its *post-merge* location and only
resolves once this repo's docs have been merged into the instance repo. This script instead gives a
developer sitting in the child repo's own checkout, before any merge, an immediately clickable link
to the current org-wide picture.

`panopticon/config.json`'s `instance_default_branch` (repo-initialization capability, kept current
on every bootstrap rerun) is always consulted first — no network call in the common case. Only when
that field is genuinely absent does this script fall back to a live GitHub API lookup, using the
same token/transport mechanism `bootstrap.py`/`sync.py`/`init_repo.py` already use (`GH_TOKEN`/
`GITHUB_TOKEN` env vars, `gh auth token` as a fallback — never a direct `gh api` subprocess call,
which depends on the separate, narrower precondition of `gh auth login`; design D11). Duplicated
rather than imported from `.sync`/`.init_repo`: this module is independently self-contained, the
same "each vendored module stands alone" precedent `sync.py` already established.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from .config import ConfigError, load_repo_config


def _resolve_token(env=None):
    """Mirrors bootstrap.py's resolve_token exactly."""
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


def _fetch_default_branch(instance, token=None, urlopen=urllib.request.urlopen):
    """One live GitHub API GET for the instance repo's metadata, reading `.default_branch`.
    Returns None on any failure — never guessed."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"https://api.github.com/repos/{instance}", headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        exc.close()
        return None
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return data.get("default_branch") or None


def build_link(instance, branch, repo):
    """Build the org-diagram deep link from already-resolved values."""
    return f"https://github.com/{instance}/blob/{branch}/docs/architecture.md#{repo}"


def resolve_branch(repo_config, env=None, urlopen=urllib.request.urlopen):
    """`instance_default_branch` from config if present; otherwise a live fallback lookup. Raises
    ConfigError when neither works — never guesses a branch name."""
    branch = repo_config.get("instance_default_branch")
    if branch:
        return branch
    branch = _fetch_default_branch(repo_config["instance"], _resolve_token(env), urlopen)
    if branch:
        return branch
    raise ConfigError(
        "panopticon/config.json has no 'instance_default_branch', and a live lookup also failed "
        "(no GH_TOKEN/GITHUB_TOKEN or gh auth token available, or the GitHub API call errored). "
        "Set GH_TOKEN/GITHUB_TOKEN, authenticate the gh CLI, or re-run the bootstrap script or "
        "'python3 -m panopticon.init_repo' once one of those is available."
    )


def main(argv=None, child_root=".", env=None, urlopen=urllib.request.urlopen):
    repo_config = load_repo_config(child_root)
    if repo_config is None:
        print("error: this repo is not Panopticon-initialized (panopticon/config.json missing)")
        return 1
    try:
        branch = resolve_branch(repo_config, env, urlopen)
    except ConfigError as exc:
        print(f"error: {exc}")
        return 1
    print(build_link(repo_config["instance"], branch, repo_config["repo"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
