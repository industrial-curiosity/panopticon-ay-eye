#!/usr/bin/env python3
"""Panopticon bootstrap installer — thin entry point.

Run from inside the child repo you want to initialize:

    export PANOPTICON_INSTANCE=acme/panopticon-instance
    curl -fsSL https://raw.githubusercontent.com/acme/panopticon-instance/main/install.py | python3

Or download and run directly:

    python3 install.py
"""
import sys


def _load_from_github(instance):
    """Download panopticon/__init__.py and panopticon/bootstrap.py from the instance repo
    and install them into sys.modules so the normal import works on the next attempt."""
    import base64
    import json
    import os
    import shutil
    import subprocess
    import types
    import urllib.error
    import urllib.request

    owner, repo = instance.split("/")

    # Reuse the same token-discovery logic that bootstrap.py uses.
    token = None
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(key):
            token = os.environ[key]
            break
    if token is None and shutil.which("gh"):
        try:
            result = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                token = result.stdout.strip()
        except Exception:
            pass

    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def _fetch(path):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref=main"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            with exc:
                body = exc.read().decode("utf-8", "replace")[:200]
            sys.exit(f"error: GitHub API {exc.code} fetching {path} from {instance}: {body}")
        return base64.b64decode(data["content"]).decode("utf-8")

    # Build a minimal panopticon package in sys.modules so that the relative
    # import inside bootstrap.py ("from . import SCHEMA_VERSION") resolves.
    pkg = types.ModuleType("panopticon")
    pkg.__path__ = []
    pkg.__package__ = "panopticon"
    exec(compile(_fetch("panopticon/__init__.py"), "panopticon/__init__.py", "exec"), pkg.__dict__)
    # Force-overwrite: a prior failed `from panopticon.bootstrap import main` can leave a stale
    # or empty `panopticon` module cached in sys.modules (e.g. an implicit namespace package from
    # an empty `panopticon/` directory already on disk) — that stale entry must not shadow the
    # freshly fetched, fully populated module the rest of this function depends on.
    sys.modules["panopticon"] = pkg

    mod = types.ModuleType("panopticon.bootstrap")
    mod.__package__ = "panopticon"
    pkg.bootstrap = mod
    sys.modules["panopticon.bootstrap"] = mod
    exec(compile(_fetch("panopticon/bootstrap.py"), "panopticon/bootstrap.py", "exec"), mod.__dict__)


try:
    from panopticon.bootstrap import main
except ModuleNotFoundError:
    # Running piped via curl from a child repo that does not contain the
    # panopticon package.  Download it from the instance repo first.
    import os as _os

    _instance = _os.environ.get("PANOPTICON_INSTANCE", "").strip()
    if not _instance:
        if not sys.stdin.isatty():
            sys.exit(
                "error: PANOPTICON_INSTANCE is not set and stdin is not a terminal.\n"
                "Set it before piping the installer:\n\n"
                "    export PANOPTICON_INSTANCE=owner/panopticon-instance\n"
                "    curl -fsSL https://raw.githubusercontent.com/$PANOPTICON_INSTANCE/main/install.py | python3"
            )
        _instance = input("Panopticon instance (owner/repo): ").strip()

    _load_from_github(_instance)
    from panopticon.bootstrap import main

if __name__ == "__main__":
    sys.exit(main() or 0)
