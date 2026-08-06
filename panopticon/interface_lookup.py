"""Load the configured instance repository's compiled interface index.

Local documentation generation may use an instance checkout, while CI already has one from its
workflow setup. When no checkout is available this module reads the single compiled index through
the GitHub Contents API, using the same token resolution as the org-diagram helper. A genuinely
missing index is an empty fresh index; malformed or unreachable existing state fails loudly.
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from .index import KIND_COMPILED, empty_index, load_index, save_index

COMPILED_INTERFACE_INDEX_PATH = "interfaces/index.json"


class InstanceInterfaceIndexError(RuntimeError):
    """The configured instance index exists or was requested but cannot be used."""


def _resolve_token(env=None):
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
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def _load_checkout(instance_root):
    path = Path(instance_root) / COMPILED_INTERFACE_INDEX_PATH
    if not path.is_file():
        return None
    try:
        return load_index(path, kind=KIND_COMPILED)
    except Exception as exc:
        raise InstanceInterfaceIndexError(
            f"compiled interface index at {path} is invalid: {exc}"
        ) from exc


def _load_live(instance, token, urlopen):
    url = f"https://api.github.com/repos/{instance}/contents/{COMPILED_INTERFACE_INDEX_PATH}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        content = base64.b64decode(payload["content"]).decode("utf-8")
        doc = json.loads(content)
        from .index import validate_index

        validate_index(doc, kind=KIND_COMPILED)
        return doc
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            exc.close()
            return empty_index(KIND_COMPILED)
        status = exc.code
        exc.close()
        raise InstanceInterfaceIndexError(
            f"could not retrieve compiled interface index from {instance}: HTTP {status}"
        ) from exc
    except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise InstanceInterfaceIndexError(
            f"could not retrieve or validate compiled interface index from {instance}: {exc}"
        ) from exc


def load_instance_interface_index(instance=None, instance_root=None, env=None,
                                  urlopen=urllib.request.urlopen):
    """Return a validated compiled index, treating a genuinely missing file as empty."""
    if instance_root is not None:
        doc = _load_checkout(instance_root)
        path = Path(instance_root) / COMPILED_INTERFACE_INDEX_PATH
        if doc is not None:
            return doc
        if not instance:
            return empty_index(KIND_COMPILED)
        # A checked-out instance without the file is the fresh-instance case; do not make a live
        # request that could turn a valid empty state into a misleading authentication failure.
        if not path.exists():
            return empty_index(KIND_COMPILED)
    if not instance:
        return empty_index(KIND_COMPILED)
    return _load_live(instance, _resolve_token(env), urlopen)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load a configured instance interface index.")
    parser.add_argument("--instance", required=True)
    parser.add_argument("--instance-root")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    doc = load_instance_interface_index(args.instance, args.instance_root)
    save_index(doc, args.output, kind=KIND_COMPILED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
