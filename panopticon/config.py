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

**Diagram config** — ``panopticon.diagram.config.json`` at the instance repo root (design D6): a
*protected* config file, excluded from ``sync-from-template``'s merge so the instance's version
always wins over whatever the template ships (design D7/D8, ``PROTECTED_CONFIG_FILES``):

    {"format": "mermaid"}

``format`` defaults to ``mermaid`` when the file is absent. Kept as its own file rather than a key
in the org config because it needs different sync treatment (protected vs. merged-and-manually-
resolved) and git's protection mechanisms operate per-path, not per-JSON-field.

``protected_paths`` (tooling-currency capability, design D6) is an org-declared array of arbitrary
paths — skills, vendored tooling modules, or other instance-repo content — customized at the
instance level and excluded from ``sync-from-template``'s merge the same way, but via
``.git/info/attributes`` rather than a ``PROTECTED_CONFIG_FILES`` registry entry, since these paths
are org-declared and open-ended rather than template-declared and fixed:

    {"protected_paths": [".agents/skills/panopticon-doc-generation/SKILL.md"]}

Defaults to an empty list when omitted.

``internal_registries`` (dependency-indexing capability) is an org-declared array of host/URL
substring strings identifying the org's own private package registry/registries (e.g. an Artifactory
or Nexus host). A dependency resolved from a manifest against a matching host is treated as internal
(same-org) rather than third-party. The same field drives both consumer-side detection and
producer-side self-registration — an org configures its registry identity once, reused in both
directions:

    {"internal_registries": ["packages.example.com"]}

Defaults to an empty list when omitted, validated the same way as ``protected_paths``.
"""

import json
from pathlib import Path

from . import SCHEMA_VERSION

ORG_CONFIG_BASENAME = "panopticon.config.json"
REPO_CONFIG_PATH = Path("panopticon") / "config.json"

CHECK_TYPES = ("init", "doc-drift", "interface-conflict", "diagram-missing")
GATING_MODES = ("blocking", "advisory")
DEFAULT_GATING = {
    "init": "blocking",
    "doc-drift": "blocking",
    "interface-conflict": "advisory",
    # Advisory at first so existing initialized repos aren't immediately blocked before they've
    # backfilled a diagram section (migration plan); orgs opt into blocking once backfilled.
    "diagram-missing": "advisory",
}

DIAGRAM_CONFIG_BASENAME = "panopticon.diagram.config.json"
DEFAULT_DIAGRAM_FORMAT = "mermaid"
# Renderers actually implemented in this codebase (design: non-goal to build a second renderer
# with no requester) — a configured format outside this set fails loudly rather than silently
# no-op-ing (group 2.4).
SUPPORTED_DIAGRAM_FORMATS = (DEFAULT_DIAGRAM_FORMAT,)

# General protected-instance-local-config primitive (design D7): registry of {path: template
# default content} pairs that sync-from-template.yml excludes from its merge entirely (the
# instance's version always wins) and field-diffs (template's top-level keys vs. the instance's)
# to warn, non-blocking, when the template adds/removes a field the instance hasn't picked up.
# Diagram config is the first entry; adding a second later is a registry entry plus a
# .gitattributes line, not a new mechanism.
PROTECTED_CONFIG_FILES = {
    DIAGRAM_CONFIG_BASENAME: {"format": DEFAULT_DIAGRAM_FORMAT},
}


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
    protected_paths = doc.get("protected_paths", [])
    if not isinstance(protected_paths, list) or not all(
        isinstance(p, str) and p for p in protected_paths
    ):
        raise ConfigError("org config: 'protected_paths' must be a list of non-empty path strings")
    internal_registries = doc.get("internal_registries", [])
    if not isinstance(internal_registries, list) or not all(
        isinstance(r, str) and r for r in internal_registries
    ):
        raise ConfigError("org config: 'internal_registries' must be a list of non-empty host/URL strings")
    return {
        "schema_version": doc.get("schema_version", SCHEMA_VERSION),
        "gating": gating,
        "workflow_ref": doc.get("workflow_ref"),
        "protected_paths": protected_paths,
        "internal_registries": internal_registries,
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


def load_diagram_config(instance_root="."):
    """Diagram format config with the ``mermaid`` default applied; a missing file yields the
    default (architecture-diagrams spec: "Default format with no config file")."""
    path = Path(instance_root) / DIAGRAM_CONFIG_BASENAME
    doc = _load_json(path, "diagram config") or {}
    fmt = doc.get("format", DEFAULT_DIAGRAM_FORMAT)
    if not isinstance(fmt, str) or not fmt:
        raise ConfigError(f"diagram config at {path}: 'format' must be a non-empty string")
    unknown = set(doc) - {"format"}
    if unknown:
        raise ConfigError(f"diagram config at {path}: unknown fields {sorted(unknown)}")
    return {"format": fmt}


def require_supported_diagram_format(fmt):
    """Loud failure for a configured format with no implemented renderer (group 2.4) — the
    diagram-existence check and the org-diagram rebuild both fail rather than silently skipping
    diagram generation (architecture-diagrams spec: "Unsupported format fails loudly")."""
    if fmt not in SUPPORTED_DIAGRAM_FORMATS:
        raise ConfigError(
            f"unknown diagram format '{fmt}' (supported: {list(SUPPORTED_DIAGRAM_FORMATS)})"
        )
