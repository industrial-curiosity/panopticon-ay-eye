"""Local sync script: refreshes managed skills, tooling, and caller workflows in a child repo.

Vendored into ``LOCAL_TOOLING_MODULES`` (``bootstrap.py``) so ``python3 -m panopticon.sync`` works
immediately after Phase 1 bootstrap with no instance-repo clone and no ``PYTHONPATH`` setup — the
same "no local instance clone required" constraint every other local-tooling module already
satisfies (design D2).

This module is deliberately self-contained rather than importing from ``.bootstrap``: bootstrap.py
is CI-only and is never vendored into a child repo (repo-initialization spec: "CI-only modules...
SHALL NOT be written to the child repo"), so a child-repo copy of this file has no `panopticon.bootstrap`
to import — `from .bootstrap import ...` fails with `ModuleNotFoundError` the moment this file is
actually run from a vendored child repo, its only real deployment target. The GitHub-API/download
primitives below are therefore duplicated from bootstrap.py rather than shared by import, mirroring
this codebase's existing precedent for the same CI/local module boundary (`init_repo.py`'s own
`ORG_SECRETS`/`ORG_VARS` duplicating bootstrap.py's). `test_sync.py` asserts these stay in sync with
bootstrap.py's copies as a drift guard.

Default behavior overwrites the child's managed skills, vendored tooling, and generated callers
unconditionally from the instance's current configuration — no per-file protection at the child
layer: the user's own review of the resulting ``git diff``/``git status`` before committing is the
safety net. ``--check-updates`` makes the entire run a pure dry run: it reports which files would
change via a git-blob-sha
comparison (GitHub's tree API already returns each file's blob ``sha``; confirmed
``sha1(f"blob {len(data)}\\0".encode() + data)`` reproduces ``git hash-object``'s output exactly)
and writes nothing.
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import load_repo_config
from .providers import ProviderConfigError, resolve_provider_contract

DEFAULT_BRANCH = "main"
SKILLS_PREFIX = ".agents/skills/"
DEFAULT_SKILLS_LOCATION = ".agents/skills"

# Mirrors bootstrap.py's TOOL_LOCATIONS exactly (test_sync.py asserts this; source of truth:
# docs/agentskills-support.md) — needed here only for _detect_existing_location's search order,
# not the interactive prompt/menu, which has no role in this already-bootstrapped-repo script.
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
    locations = [DEFAULT_SKILLS_LOCATION]
    for _, tool_locations in TOOL_LOCATIONS.values():
        for loc in tool_locations:
            if loc not in locations:
                locations.append(loc)
    return locations


def _detect_existing_location(child_root="."):
    for loc in candidate_locations():
        d = Path(child_root) / loc
        if d.is_dir() and any(p.name.startswith("panopticon-") for p in d.iterdir()):
            return loc
    return None


# ── GitHub API helpers (duplicated from bootstrap.py; see module docstring) ────────────────────

def _api_headers(token=None):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


_RETRYABLE_STATUS = {500, 502, 503, 504}


def _rate_limit_delay(status, headers, body, now, fallback):
    """Return a GitHub-directed retry delay, or None for a non-rate-limit response."""
    headers = headers or {}
    retry_after = headers.get("Retry-After")
    remaining = headers.get("X-RateLimit-Remaining")
    reset = headers.get("X-RateLimit-Reset")
    identified = (
        status == 429
        or retry_after is not None
        or str(remaining).strip() == "0"
        or "rate limit" in body.lower()
    )
    if status != 429 and (status != 403 or not identified):
        return None
    if retry_after is not None:
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            pass
    if reset is not None:
        try:
            return max(0.0, float(reset) - now())
        except (TypeError, ValueError):
            pass
    return fallback


def _api_get(url, token=None, urlopen=urllib.request.urlopen, max_attempts=3, sleep=time.sleep,
             now=time.time, print_fn=print):
    req = urllib.request.Request(url, headers=_api_headers(token))
    last_error = None
    for attempt in range(1, max_attempts + 1):
        rate_limited = False
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            headers = exc.headers
            with exc:
                body = exc.read().decode("utf-8", "replace")[:400]
            last_error = f"GitHub API {exc.code} for {url}: {body}"
            fallback = 2 ** (attempt - 1)
            delay = _rate_limit_delay(exc.code, headers, body, now, fallback)
            if delay is None and exc.code not in _RETRYABLE_STATUS:
                raise RuntimeError(last_error)
            rate_limited = delay is not None
            if not rate_limited:
                delay = fallback
        except urllib.error.URLError as exc:
            last_error = f"GitHub API request failed for {url}: {exc.reason}"
            delay = 2 ** (attempt - 1)
        if attempt < max_attempts:
            if rate_limited:
                print_fn(f"  GitHub API rate limited; retrying in {int(delay + 0.999)} seconds...")
            sleep(delay)
    raise RuntimeError(last_error)


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


def resolve_token(env=None):
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


def download_skills(owner, repo, ref, tree, token=None, child_root=".", dest_location=None,
                    urlopen=urllib.request.urlopen):
    dest_location = dest_location if dest_location is not None else DEFAULT_SKILLS_LOCATION
    blobs = [
        item for item in tree
        if item["type"] == "blob"
        and item["path"].startswith(SKILLS_PREFIX + "panopticon-")
    ]
    count = 0
    for item in blobs:
        path = item["path"]
        relative = path[len(SKILLS_PREFIX):]
        local = Path(child_root) / dest_location / relative
        local.parent.mkdir(parents=True, exist_ok=True)
        content = _fetch_file_bytes(owner, repo, path, ref, token, urlopen)
        local.write_bytes(content)
        count += 1
    return count


def download_local_tooling(owner, repo, ref, tree, token=None, child_root=".",
                           urlopen=urllib.request.urlopen):
    """Fetch the complete managed directory before writing any of its files.

    This lets an older sync entrypoint acquire a newly-required module as part
    of the same reconciliation.  Applying is additive/overwrite-only: no
    local path is removed when the source directory no longer contains it.
    """
    entries = _tooling_tree_entries(tree)
    staged = [
        (item["path"], _fetch_file_bytes(owner, repo, item["path"], ref, token, urlopen))
        for item in entries
    ]
    for path, content in staged:
        local = Path(child_root) / path
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(content)
    return len(staged)


# ── Sync-specific logic ──────────────────────────────────────────────────────────────────────

def git_blob_sha(data):
    """The git blob sha1 for `data`'s exact bytes — matches `git hash-object`'s output."""
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _skill_tree_entries(tree):
    return [
        item for item in tree
        if item["type"] == "blob" and item["path"].startswith(SKILLS_PREFIX + "panopticon-")
    ]


def _tooling_tree_entries(tree):
    protected = {"panopticon/config.json", "panopticon/.gitignore"}
    return [
        item for item in tree
        if item["type"] == "blob"
        and item["path"].startswith("panopticon/")
        and item["path"] not in protected
    ]


def _compare(local, item, relative):
    if not local.is_file():
        return [f"{relative} would be created (missing locally)"]
    if git_blob_sha(local.read_bytes()) != item["sha"]:
        return [f"{relative} would be updated (content differs from the instance's current copy)"]
    return []


def _fetch_org_config(owner, repo, ref, token=None, urlopen=urllib.request.urlopen):
    """Fetch the instance configuration required to render managed child callers."""
    try:
        return json.loads(
            _fetch_file_bytes(owner, repo, "panopticon.config.json", ref, token, urlopen)
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(
            f"invalid panopticon.config.json fetched from {owner}/{repo}@{ref}: {exc}"
        ) from exc


def _caller_updates(child_root, instance, ref, contract, default_branch):
    """Return managed caller paths whose generated content differs from the child copy."""
    # This import happens only after the complete managed directory is in
    # place.  It is deliberately not an import-time dependency of sync.py:
    # older children may be missing this newly introduced module.
    from .callers import CALLER_WORKFLOWS, caller_workflow_text

    updates = []
    for name in CALLER_WORKFLOWS:
        relative = f".github/workflows/{name}"
        expected = caller_workflow_text(name, instance, ref, contract, default_branch)
        path = Path(child_root) / relative
        if not path.is_file():
            updates.append((relative, expected, "would be created (missing locally)"))
        elif path.read_text(encoding="utf-8") != expected:
            updates.append((relative, expected, "would be updated (content differs from generated caller)"))
    return updates


def _caller_updates_from_source(source, child_root, instance, ref, contract, default_branch):
    """Render caller preview from the canonical remote module without writing it.

    Older children may not yet contain callers.py.  ``--check-updates`` must
    remain read-only, so it loads the trusted instance copy in memory rather
    than creating the module merely to preview the generated callers.
    """
    namespace = {"__name__": "panopticon.callers_preview"}
    exec(compile(source, "panopticon/callers.py", "exec"), namespace)
    updates = []
    for name in namespace["CALLER_WORKFLOWS"]:
        relative = f".github/workflows/{name}"
        expected = namespace["caller_workflow_text"](
            name, instance, ref, contract, default_branch
        )
        path = Path(child_root) / relative
        if not path.is_file():
            updates.append((relative, expected, "would be created (missing locally)"))
        elif path.read_text(encoding="utf-8") != expected:
            updates.append((relative, expected, "would be updated (content differs from generated caller)"))
    return updates


def _write_callers(child_root, updates):
    for relative, content, _ in updates:
        path = Path(child_root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_updates(tree, child_root, child_location, caller_updates=()):
    """Pure dry run: compare each relevant tree entry's blob sha against the child's local file,
    using no network calls beyond the already-fetched tree. Returns a list of finding strings;
    writes nothing."""
    findings = []
    for item in _skill_tree_entries(tree):
        relative = item["path"][len(SKILLS_PREFIX):]
        local = Path(child_root) / child_location / relative
        findings.extend(_compare(local, item, relative))
    for item in _tooling_tree_entries(tree):
        relative = item["path"]
        local = Path(child_root) / relative
        findings.extend(_compare(local, item, relative))
    findings.extend(f"{relative} {reason}" for relative, _, reason in caller_updates)
    return findings


def main(argv=None, env=None, child_root=".", urlopen=urllib.request.urlopen):
    env = env if env is not None else os.environ
    parser = argparse.ArgumentParser(
        description="Refresh managed Panopticon skills, tooling, and workflow callers in this child repo."
    )
    parser.add_argument("--check-updates", action="store_true",
                        help="report which files would change; write nothing")
    args = parser.parse_args(argv)

    repo_config = load_repo_config(child_root)
    if repo_config is None:
        print("error: this repo is not Panopticon-initialized (panopticon/config.json missing)")
        return 1
    owner, repo = repo_config["instance"].split("/")

    token = resolve_token(env)
    default_branch = env.get("PANOPTICON_DEFAULT_BRANCH", DEFAULT_BRANCH)
    workflow_ref = repo_config.get("workflow_ref", default_branch)
    location = _detect_existing_location(child_root) or DEFAULT_SKILLS_LOCATION

    try:
        org_config = _fetch_org_config(owner, repo, workflow_ref, token, urlopen)
        contract = resolve_provider_contract(org_config.get("llm"))
    except (RuntimeError, ProviderConfigError) as exc:
        print(f"error: could not read valid instance provider configuration: {exc}")
        return 1

    tree = _fetch_tree(owner, repo, default_branch, token, urlopen)
    callers_path = Path(child_root) / "panopticon/callers.py"
    tooling_findings = check_updates(tree, child_root, location)

    if callers_path.is_file():
        callers = _caller_updates(
            child_root, repo_config["instance"], workflow_ref, contract, default_branch
        )
    else:
        caller_source = _fetch_file_bytes(
            owner, repo, "panopticon/callers.py", default_branch, token, urlopen
        )
        callers = _caller_updates_from_source(
            caller_source, child_root, repo_config["instance"], workflow_ref, contract,
            default_branch,
        )
    findings = tooling_findings + [
        f"{relative} {reason}" for relative, _, reason in callers
    ]

    if args.check_updates:
        if not findings:
            print("Everything is current — no managed skills, tooling, or workflow callers would change.")
        else:
            for finding in findings:
                print(f"  {finding}")
        return 0

    if not findings:
        print("Everything is current — no managed skills, tooling, or workflow callers changed.")
        return 0

    n_skills = download_skills(owner, repo, default_branch, tree, token, child_root, location, urlopen)
    n_modules = download_local_tooling(owner, repo, default_branch, tree, token, child_root, urlopen)
    # The staged directory may have added callers.py or changed its renderer.
    # Read the canonical contract only after that full resource set is applied.
    callers = _caller_updates(
        child_root, repo_config["instance"], workflow_ref, contract, default_branch
    )
    _write_callers(child_root, callers)
    print(
        f"{n_skills} skill file(s), {n_modules} tooling module(s), and {len(callers)} workflow caller(s) synced from "
        f"{owner}/{repo}@{default_branch}."
    )
    print("Review `git diff`/`git status` before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
