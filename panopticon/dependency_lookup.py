"""Dependency-indexing capability: registry-host detection and instance cross-reference.

Two independent lookups a candidate dependency needs, neither requiring org-specific code:

- ``is_internal_registry`` — pure, no network: does a manifest-resolved host/URL match one of the
  org's declared ``internal_registries`` (panopticon/config.py)? Used both for consumer-side
  detection (does this look like ours) and producer-side self-registration (does our own publish
  step target one of these hosts) — the same config field, two directions.
- ``lookup_registered_producer`` — is a candidate's canonical name already self-registered as a
  producer in the instance repo's compiled dependency index? Prefers a local instance-repo
  checkout (a plain filesystem read: CI already has one, since ``panopticon-pr.yml`` /
  ``panopticon-merge.yml`` run a full ``actions/checkout`` of the instance repo before any check
  runs — the same precondition every other CI-side instance-repo read in this codebase relies on,
  e.g. ``config.load_org_config``, the compiled interface index; no live API call, no new auth
  mechanism needed there). Falls back to a live, best-effort GitHub API read of that one file only
  when no checkout is available (the local-agent case) — same token-resolution precedent as
  ``org_diagram_link.py``'s ``_resolve_token``/``_fetch_default_branch``: ``GH_TOKEN``/
  ``GITHUB_TOKEN`` env vars, then ``gh auth token``, one GET, ``None`` on any failure. Never
  guesses; callers fall through to hint/LLM resolution when this returns ``None``.
"""

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from .dependencies import KIND_COMPILED, DependencyIndexValidationError, load_index

COMPILED_DEPENDENCY_INDEX_PATH = "dependencies/index.json"


def is_internal_registry(url_or_host, internal_registries):
    """Whether ``url_or_host`` resolves from one of the org's declared registry hosts.

    A plain substring match against each declared entry — entries are already host/URL substrings
    (panopticon/config.py's ``internal_registries``), so this stays a pure function with no URL
    parsing beyond a straightforward containment check.
    """
    if not url_or_host or not internal_registries:
        return False
    return any(registry in url_or_host for registry in internal_registries)


def _resolve_token(env=None):
    """Mirrors org_diagram_link.py's ``_resolve_token`` exactly (same precedent, duplicated per the
    "each vendored module stands alone" convention)."""
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


def _owner_for_name(doc, name):
    entries = doc.get("dependencies", {}).get(name, [])
    for entry in entries:
        if entry.get("owner"):
            return entry["owner"]
    return None


def _lookup_from_checkout(instance_root, name):
    path = Path(instance_root) / COMPILED_DEPENDENCY_INDEX_PATH
    if not path.is_file():
        return None
    try:
        doc = load_index(path, kind=KIND_COMPILED)
    except DependencyIndexValidationError:
        return None
    return _owner_for_name(doc, name)


def _lookup_from_live_api(instance, name, token=None, urlopen=urllib.request.urlopen):
    """One live GitHub Contents API GET for the instance's compiled dependency index. Returns the
    owner dict, or None on any failure or absence — never guessed."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{instance}/contents/{COMPILED_DEPENDENCY_INDEX_PATH}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
        content = base64.b64decode(payload["content"]).decode("utf-8")
        doc = json.loads(content)
    except urllib.error.HTTPError as exc:
        exc.close()
        return None
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return None
    return _owner_for_name(doc, name)


def lookup_registered_producer(name, instance=None, instance_root=None, env=None,
                                urlopen=urllib.request.urlopen):
    """The owner dict already self-registered for ``name`` in the instance's compiled dependency
    index, or None when unresolvable — never a guess, callers fall through to hint/LLM resolution.

    Prefers ``instance_root`` (a local checkout — always available in CI, per the module docstring)
    when it contains a compiled dependency index. Falls back to a live API read against ``instance``
    (e.g. ``"acme/panopticon-instance"``) only when no usable checkout was given.
    """
    if instance_root is not None:
        owner = _lookup_from_checkout(instance_root, name)
        if owner is not None:
            return owner
        if Path(instance_root, COMPILED_DEPENDENCY_INDEX_PATH).is_file():
            return None
    if not instance:
        return None
    return _lookup_from_live_api(instance, name, _resolve_token(env), urlopen)
