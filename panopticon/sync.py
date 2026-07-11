"""Local sync script (tooling-currency capability): pulls the instance repo's current skills and
vendored local-tooling modules into an already-bootstrapped child repo, on demand.

Vendored into ``LOCAL_TOOLING_MODULES`` (``bootstrap.py``) so ``python3 -m panopticon.sync`` works
immediately after Phase 1 bootstrap with no instance-repo clone and no ``PYTHONPATH`` setup — the
same "no local instance clone required" constraint every other local-tooling module already
satisfies (design D2).

Default behavior overwrites the child's skills and vendored tooling unconditionally from the
instance's current default branch — no per-file protection at the child layer (design D5): the
user's own review of the resulting ``git diff``/``git status`` before committing is the safety net,
the same trust model ``bootstrap.py``'s existing idempotent overwrite already uses. ``--check-updates``
makes the entire run a pure dry run: it reports which files would change via a git-blob-sha
comparison (GitHub's tree API already returns each file's blob ``sha``; confirmed
``sha1(f"blob {len(data)}\\0".encode() + data)`` reproduces ``git hash-object``'s output exactly)
and writes nothing.
"""

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

from .bootstrap import (
    DEFAULT_BRANCH,
    DEFAULT_SKILLS_LOCATION,
    LOCAL_TOOLING_MODULES,
    SKILLS_PREFIX,
    _detect_existing_location,
    _fetch_tree,
    download_local_tooling,
    download_skills,
    resolve_token,
)
from .config import load_repo_config


def git_blob_sha(data):
    """The git blob sha1 for `data`'s exact bytes — matches `git hash-object`'s output."""
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _skill_tree_entries(tree):
    return [
        item for item in tree
        if item["type"] == "blob" and item["path"].startswith(SKILLS_PREFIX + "panopticon-")
    ]


def _tooling_tree_entries(tree):
    wanted = {f"panopticon/{name}" for name in LOCAL_TOOLING_MODULES}
    return [item for item in tree if item["type"] == "blob" and item["path"] in wanted]


def _compare(local, item, relative):
    if not local.is_file():
        return [f"{relative} would be created (missing locally)"]
    if git_blob_sha(local.read_bytes()) != item["sha"]:
        return [f"{relative} would be updated (content differs from the instance's current copy)"]
    return []


def check_updates(tree, child_root, child_location):
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
    return findings


def main(argv=None, env=None, child_root=".", urlopen=urllib.request.urlopen):
    env = env if env is not None else os.environ
    parser = argparse.ArgumentParser(
        description="Pull the instance repo's current skills and vendored tooling into this child repo."
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
    location = _detect_existing_location(child_root) or DEFAULT_SKILLS_LOCATION

    tree = _fetch_tree(owner, repo, default_branch, token, urlopen)
    findings = check_updates(tree, child_root, location)

    if args.check_updates:
        if not findings:
            print("Everything is current — no skills or vendored tooling would change.")
        else:
            for finding in findings:
                print(f"  {finding}")
        return 0

    if not findings:
        print("Everything is current — no skills or vendored tooling changed.")
        return 0

    n_skills = download_skills(owner, repo, default_branch, tree, token, child_root, location, urlopen)
    n_modules = download_local_tooling(owner, repo, default_branch, token, child_root, urlopen)
    print(
        f"{n_skills} skill file(s) and {n_modules} tooling module(s) synced from "
        f"{owner}/{repo}@{default_branch}."
    )
    print("Review `git diff`/`git status` before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
