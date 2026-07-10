"""Child-repo initialization finalization step.

After the bootstrap installer (``install.py``) has wired skills and workflows, and after the
user's agent has generated documentation and the local interface index via the bundled skills,
this module validates those artifacts and writes ``panopticon/config.json`` — the initialization
flag — as the last artifact created.

Run from the child repo::

    python3 -m panopticon.init_repo --instance acme/panopticon-instance

Division of labor (repo-initialization spec):

- **Bootstrap** (``install.py`` / ``panopticon/bootstrap.py``): downloads skills, wires
  caller workflows, prints agent prompts.  No local instance clone required.
- **Agent**: generates docs and interface index using the installed skills.
- **Finalization** (this module): validates agent-produced docs and index, writes
  ``panopticon/config.json`` only after validation passes.  Re-running is idempotent.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import load_repo_config, save_repo_config
from .docs import validate_docs
from .index import KIND_LOCAL, IndexValidationError, load_index

ORG_SECRETS = ("PANOPTICON_LLM_API_KEY", "PANOPTICON_INSTANCE_TOKEN")
ORG_VARS = ("PANOPTICON_LLM_ENDPOINT", "PANOPTICON_LLM_MODEL")

_EXISTING_DOC_DIRS = ("docs", "doc", "documentation")

CALLER_WORKFLOW_FOR_REF = Path(".github") / "workflows" / "panopticon-pr.yml"
_USES_REF_RE = re.compile(r"^\s*uses:\s*\S+/\.github/workflows/\S+@(\S+)\s*$", re.MULTILINE)

FALLBACK_WORKFLOW_REF = "main"


def discover_workflow_ref(child_root):
    """Parse the ref bootstrap.py actually wired into the caller workflow's `uses:` line.

    Returns None when the file is missing or unparseable — the ref bootstrap.py used (default
    branch or an org-pinned tag/branch) is baked into that line, so re-deriving it here is the
    only way to keep the recorded workflow_ref from silently diverging from what was wired.
    """
    try:
        text = (Path(child_root) / CALLER_WORKFLOW_FOR_REF).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    match = _USES_REF_RE.search(text)
    return match.group(1) if match else None


def _fallback_workflow_ref(child_root, runner=subprocess.run):
    """Last-resort ref when the caller workflow can't be read/parsed: the child repo's own
    checked-out branch — never a hardcoded tag, which would silently imply one exists."""
    try:
        result = runner(
            ["git", "-C", str(child_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return FALLBACK_WORKFLOW_REF
    branch = result.stdout.strip()
    if result.returncode == 0 and branch and branch != "HEAD":
        return branch
    return FALLBACK_WORKFLOW_REF


def detect_docs_location(child_root, configured=None, requested=None, prompt=input):
    """Adopt existing docs; otherwise ask (default ``docs/``). Returns a repo-relative path."""
    if configured:
        return configured
    if requested:
        return requested
    child_root = Path(child_root)
    for candidate in _EXISTING_DOC_DIRS:
        if (child_root / candidate).is_dir() and any((child_root / candidate).iterdir()):
            return candidate
    answer = prompt("Documentation location for this repo [docs]: ").strip()
    return answer or "docs"


def validate_child(child_root, repo_name, docs_location):
    """Deterministic validation of agent-produced docs and index; returns unmet requirements."""
    problems = list(validate_docs(Path(child_root) / docs_location))
    try:
        load_index(Path(child_root) / "panopticon" / "index.json", kind=KIND_LOCAL, repo=repo_name)
    except IndexValidationError as exc:
        problems.extend(f"local index: {p}" for p in exc.problems)
    return problems


def _gh_api_names(runner, url, jq_expr):
    """Run a gh api call and return a set of names, or None on failure."""
    try:
        result = runner(
            ["gh", "api", url, "--jq", jq_expr],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return set(result.stdout.split())


def _manual_verification_message(org, reason):
    """Concrete web-UI + gh-CLI steps for verifying org secrets/variables by hand.

    Used whenever automated verification isn't possible (``gh`` missing, unauthenticated, or
    lacking org-admin permissions) — never framed as an error, since the items may well be
    configured correctly.
    """
    settings_url = f"https://github.com/organizations/{org}/settings/secrets/actions"
    return (
        f"{reason} Verify manually that these are configured:\n"
        f"    secrets:   {', '.join(ORG_SECRETS)}\n"
        f"    variables: {', '.join(ORG_VARS)}\n"
        f"  Web UI: {settings_url} (secrets and variables are separate tabs)\n"
        f"  Or locally via the gh CLI (run `gh auth login` first if not already authenticated):\n"
        f"    gh secret list --org {org}\n"
        f"    gh variable list --org {org}"
    )


def _check_gh_api_kind(org, runner, endpoint, collection_key, items, kind):
    """Check one kind (secrets or variables) via `gh api`; returns a list of report lines."""
    settings_url = f"https://github.com/organizations/{org}/settings/secrets/actions"
    existing = _gh_api_names(runner, f"orgs/{org}/actions/{endpoint}", f".{collection_key}[].name")
    if existing is None:
        return [_manual_verification_message(
            org, f"could not query org {kind}s via `gh api` (not authenticated, or lacking "
            "org-admin permissions)."
        )]
    return [
        f"missing org-level {kind} {name}: create it at {settings_url} and grant access to all "
        "repositories Panopticon should cover. See docs/setup-guide.md. Workflow wiring is not "
        "complete until it exists."
        for name in items if name not in existing
    ]


def verify_org_secrets(org, runner=subprocess.run):
    """Report-only org secret/variable verification via the gh CLI. Never blocks local init."""
    if shutil.which("gh") is None:
        return [_manual_verification_message(org, "the 'gh' CLI is not installed.")]

    report = _check_gh_api_kind(org, runner, "secrets", "secrets", ORG_SECRETS, "secret")
    report += _check_gh_api_kind(org, runner, "variables", "variables", ORG_VARS, "variable")

    if not report:
        report.append(
            f"all org-level secrets present: {', '.join(ORG_SECRETS)}; "
            f"all org-level variables present: {', '.join(ORG_VARS)}"
        )
    return report


def initialize(child_root, repo_name, instance, docs_location=None, workflow_ref=None,
               skip_secret_check=False, prompt=input):
    """Finalization pass: validate agent output and write panopticon/config.json.

    `workflow_ref` defaults to None, meaning "derive it" — read from the ref bootstrap.py already
    wired into the caller workflow's `uses:@ref` line, falling back to the child repo's checked-out
    branch only if that file is missing or unparseable. Pass an explicit value to override.

    Returns (exit_code, messages). Idempotent — safe to re-run.
    """
    messages = []
    child_root = Path(child_root)
    if workflow_ref is None:
        workflow_ref = discover_workflow_ref(child_root) or _fallback_workflow_ref(child_root)
    existing = load_repo_config(child_root)
    if existing:
        messages.append("repo already initialized — updating in place (idempotent re-init)")
    requested = docs_location
    docs_location = detect_docs_location(
        child_root,
        configured=(existing or {}).get("docs_location"),
        requested=requested,
        prompt=prompt,
    )

    problems = validate_child(child_root, repo_name, docs_location)
    if problems:
        messages.append("initialization requirements not met — panopticon/config.json NOT written:")
        messages.extend(f"  - {p}" for p in problems)
        messages.append(
            "Generate/repair the docs and index with your agent (panopticon-doc-generation, "
            "panopticon-interface-naming skills), then re-run the finalization step."
        )
        return 1, messages

    if not skip_secret_check:
        messages.extend(verify_org_secrets(instance.split("/")[0]))

    save_repo_config(
        {
            "repo": repo_name,
            "instance": instance,
            "workflow_ref": workflow_ref,
            "docs_location": docs_location,
        },
        repo_root=child_root,
    )
    messages.append(f"wrote panopticon/config.json (repo={repo_name}, docs_location={docs_location})")
    return 0, messages


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Finalize Panopticon initialization for a child repo."
    )
    parser.add_argument("--child", default=".", help="path to the child repo (default: current directory)")
    parser.add_argument("--repo-name", help="child repo name (default: directory name)")
    parser.add_argument("--instance", required=True, help="instance repo as owner/name")
    parser.add_argument("--workflow-ref", default=None,
                        help="ref recorded in panopticon/config.json (default: auto-detected from "
                             "the wired caller workflow's uses:@ref line)")
    parser.add_argument("--docs-location", help="documentation location (skips adoption/prompt)")
    parser.add_argument("--skip-secret-check", action="store_true")
    args = parser.parse_args(argv)

    code, messages = initialize(
        child_root=args.child,
        repo_name=args.repo_name or Path(args.child).resolve().name,
        instance=args.instance,
        docs_location=args.docs_location,
        workflow_ref=args.workflow_ref,
        skip_secret_check=args.skip_secret_check,
    )
    for message in messages:
        print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
