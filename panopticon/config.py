"""Configuration files: the instance repo's org config and the child repo's repo config.

**Org config** — ``panopticon.config.json`` at the instance repo root (design D2):

    {
      "schema_version": 1,
      "gating": {"init": "blocking", "doc-drift": "blocking", "interface-conflict": "advisory"},
      "workflow_ref": "v1"
    }

Gating modes are per check type; the defaults above implement the settled gating policy
(init/doc-drift fail, interface conflicts advisory) and orgs may adjust each in both directions.
Workflows must read these modes rather than hardcoding outcomes. ``workflow_ref`` is the git ref
(tag or branch) at which init wires child caller workflows to the instance's reusable workflows.
When omitted, callers resolve the effective ref themselves (e.g. the instance repo's default
branch, fetched live) — this module has no network access and so has no way to know that ref
locally; it reports ``None`` rather than guessing a value like a tag that may not exist.

**Repo config** — ``panopticon/config.json`` in a child repo: doubles as the initialization flag
and records repo-level settings:

    {
      "schema_version": 1,
      "repo": "svc-a",
      "instance": "acme/panopticon-instance",
      "workflow_ref": "v1",
      "docs_location": "docs"
    }
"""

import json
from pathlib import Path

from . import SCHEMA_VERSION

ORG_CONFIG_BASENAME = "panopticon.config.json"
REPO_CONFIG_PATH = Path("panopticon") / "config.json"

CHECK_TYPES = ("init", "doc-drift", "interface-conflict")
GATING_MODES = ("blocking", "advisory")
DEFAULT_GATING = {"init": "blocking", "doc-drift": "blocking", "interface-conflict": "advisory"}


class ConfigError(Exception):
    pass


def _load_json(path, description):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{description} at {path} is not valid JSON: {exc}")
    if not isinstance(doc, dict):
        raise ConfigError(f"{description} at {path} must be a JSON object")
    return doc


def load_org_config(instance_root="."):
    """Org config with defaults applied; a missing file yields pure defaults."""
    path = Path(instance_root) / ORG_CONFIG_BASENAME
    doc = _load_json(path, "org config") or {}
    gating = dict(DEFAULT_GATING)
    for check, mode in (doc.get("gating") or {}).items():
        if check not in CHECK_TYPES:
            raise ConfigError(f"org config: unknown check type '{check}' (known: {list(CHECK_TYPES)})")
        if mode not in GATING_MODES:
            raise ConfigError(f"org config: gating for '{check}' must be one of {list(GATING_MODES)}, got '{mode}'")
        gating[check] = mode
    return {
        "schema_version": doc.get("schema_version", SCHEMA_VERSION),
        "gating": gating,
        "workflow_ref": doc.get("workflow_ref"),
    }


def gating_mode(org_config, check):
    if check not in CHECK_TYPES:
        raise ConfigError(f"unknown check type '{check}'")
    return org_config["gating"][check]


def load_repo_config(repo_root="."):
    """Child repo config, or None when the repo is not Panopticon-initialized."""
    path = Path(repo_root) / REPO_CONFIG_PATH
    doc = _load_json(path, "repo config")
    if doc is None:
        return None
    missing = [field for field in ("repo", "instance", "docs_location") if not doc.get(field)]
    if missing:
        raise ConfigError(f"repo config at {path} is missing required fields: {missing}")
    return doc


def save_repo_config(config, repo_root="."):
    path = Path(repo_root) / REPO_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION, **config}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
