"""Child-repo initialization, run from an instance-fork checkout.

Division of labor (repo-initialization spec): the **user's agent** generates the four-layer docs
and the local interface index via the bundled skills (panopticon-doc-generation,
panopticon-interface-naming — no ``PANOPTICON_LLM_*`` needed locally). This deterministic tool
then:

1. adopts or asks for the documentation location (existing docs win; default ``docs/``),
2. validates that the agent-produced docs and index meet requirements,
3. wires thin caller workflows referencing the instance repo's reusable workflows at the
   org-configured ref,
4. verifies org-level secrets exist (report-only — missing secrets never block local init), and
5. writes ``panopticon/config.json`` — the initialization flag — **only after validation passes**.

Re-initialization is idempotent: workflows, docs wiring, and config are updated in place; nothing
is duplicated.

Usage (from the instance repo checkout)::

    python3 -m panopticon.init_repo --child ../svc-a --instance acme/panopticon-instance
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .config import DEFAULT_WORKFLOW_REF, load_org_config, load_repo_config, save_repo_config
from .docs import validate_docs
from .index import KIND_LOCAL, IndexValidationError, load_index

CALLER_WORKFLOWS = ("panopticon-pr.yml", "panopticon-merge.yml", "panopticon-pr-close.yml")
ORG_SECRETS = ("PANOPTICON_LLM_API_KEY", "PANOPTICON_LLM_ENDPOINT", "PANOPTICON_INSTANCE_TOKEN")

_CALLER_HEADER = (
    "# Wired by Panopticon init — a thin reference to the shared workflow in the instance repo.\n"
    "# Do not edit by hand; re-run the init tooling to update. Secrets are org-level; this repo\n"
    "# configures none of its own.\n"
)

_EXISTING_DOC_DIRS = ("docs", "doc", "documentation")


def caller_workflow_text(name, instance, ref, default_branch):
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


def wire_workflows(child_root, instance, ref, default_branch):
    """Write/refresh the three caller workflows in place; returns their paths."""
    workflows_dir = Path(child_root) / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in CALLER_WORKFLOWS:
        path = workflows_dir / name
        path.write_text(caller_workflow_text(name, instance, ref, default_branch), encoding="utf-8")
        written.append(path)
    return written


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


def verify_org_secrets(org, runner=subprocess.run):
    """Report-only org secret verification via the gh CLI. Never blocks local init."""
    report = []
    if shutil.which("gh") is None:
        report.append(
            "could not verify org secrets: the 'gh' CLI is not installed. Verify manually that "
            f"the org-level secrets {', '.join(ORG_SECRETS)} exist (GitHub → org Settings → "
            "Secrets and variables → Actions)."
        )
        return report
    try:
        result = runner(
            ["gh", "api", f"orgs/{org}/actions/secrets", "--jq", ".secrets[].name"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result = None
        report.append(f"could not verify org secrets ({exc}); verify manually.")
    if result is not None:
        if result.returncode != 0:
            report.append(
                f"could not verify org secrets (gh api failed: {result.stderr.strip()[:200]}). "
                "Verify manually or re-run with credentials that can read org secrets."
            )
        else:
            existing = set(result.stdout.split())
            for secret in ORG_SECRETS:
                if secret not in existing:
                    report.append(
                        f"missing org-level secret {secret}: create it at "
                        f"https://github.com/organizations/{org}/settings/secrets/actions and "
                        "grant access to all repositories Panopticon should cover. See "
                        "docs/setup-guide.md. Workflow wiring is not complete until it exists."
                    )
    if not report:
        report.append(f"all org-level secrets present: {', '.join(ORG_SECRETS)}")
    return report


def initialize(child_root, repo_name, instance, workflow_ref, docs_location, default_branch="main",
               skip_secret_check=False, prompt=input):
    """Full init pass. Returns (exit_code, messages)."""
    messages = []
    child_root = Path(child_root)
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
    if docs_location != requested and not existing:
        messages.append(f"documentation location: {docs_location}/")

    problems = validate_child(child_root, repo_name, docs_location)
    if problems:
        messages.append("initialization requirements not met — panopticon/config.json NOT written:")
        messages.extend(f"  - {p}" for p in problems)
        messages.append(
            "Generate/repair the docs and index with your agent (panopticon-doc-generation, "
            "panopticon-interface-naming skills), then re-run init."
        )
        return 1, messages

    for path in wire_workflows(child_root, instance, workflow_ref, default_branch):
        messages.append(f"wired {path.relative_to(child_root)}")

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
    parser = argparse.ArgumentParser(description="Initialize a child repo for Panopticon.")
    parser.add_argument("--child", required=True, help="path to the child repo checkout")
    parser.add_argument("--repo-name", help="child repo name (default: directory name)")
    parser.add_argument("--instance", required=True, help="instance repo as owner/name")
    parser.add_argument("--workflow-ref", help="ref for caller workflows (default: org config workflow_ref)")
    parser.add_argument("--docs-location", help="documentation location (skips adoption/prompt)")
    parser.add_argument("--default-branch", default="main")
    parser.add_argument("--instance-root", default=".", help="instance checkout holding panopticon.config.json")
    parser.add_argument("--skip-secret-check", action="store_true")
    args = parser.parse_args(argv)

    workflow_ref = args.workflow_ref or load_org_config(args.instance_root).get(
        "workflow_ref", DEFAULT_WORKFLOW_REF
    )
    code, messages = initialize(
        child_root=args.child,
        repo_name=args.repo_name or Path(args.child).resolve().name,
        instance=args.instance,
        workflow_ref=workflow_ref,
        docs_location=args.docs_location,
        default_branch=args.default_branch,
        skip_secret_check=args.skip_secret_check,
    )
    for message in messages:
        print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
