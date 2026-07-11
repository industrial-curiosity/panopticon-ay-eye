"""Advisory-only tooling-currency PR check (CI only, not vendored into child repos).

Warns when a child repo's wired ``panopticon-pr.yml`` caller-workflow ref no longer resolves to
the instance repo's current default-branch tip, and separately when the child's downloaded
``panopticon-*`` skills or vendored local-tooling modules differ in content from the instance
repo's current copies. Both checks run against the instance repo checkout the PR workflow already
performs (``.panopticon-instance`` by convention) — no additional network calls beyond the
``git ls-remote`` the ref-alignment check needs.

This module never gates (tooling-currency capability: "always advisory") — it has no entry in
``panopticon.config``'s ``CHECK_TYPES``/``DEFAULT_GATING`` and its ``main()`` always exits ``0``,
unlike drift.py/currency.py/diagram_check.py's business-verdict exit-code contract (0=clean,
2=problems, other=operational failure). Findings are plain ``::warning::`` lines, never fed into
``panopticon/report.py``'s combined TL;DR report (design D4) — remediation here ("run the sync
script") doesn't fit that report's must-fix-before-merge action vocabulary.
"""

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_INSTANCE_ROOT = ".panopticon-instance"


def check_workflow_ref(child_root=".", instance_root=DEFAULT_INSTANCE_ROOT, runner=subprocess.run):
    """Workflow-ref alignment check (design D1): resolve the child's wired ``uses:@ref`` via
    ``git ls-remote`` against the instance checkout's current ``HEAD`` (the commit the PR
    workflow's "Check out instance repo" step already lands on, since it passes no ``ref:``
    override). Returns a finding string, or ``None`` when aligned."""
    from .init_repo import discover_workflow_ref

    ref = discover_workflow_ref(child_root)
    if ref is None:
        return (
            "could not determine the wired workflow ref from "
            ".github/workflows/panopticon-pr.yml"
        )

    ls_remote = runner(
        ["git", "-C", str(instance_root), "ls-remote", "origin", ref],
        capture_output=True, text=True, timeout=30,
    )
    resolved = ls_remote.stdout.split()[0] if ls_remote.returncode == 0 and ls_remote.stdout.strip() else None
    if not resolved:
        return f"wired workflow ref '{ref}' no longer resolves to any commit on the instance repo"

    head = runner(
        ["git", "-C", str(instance_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10,
    )
    current = head.stdout.strip() if head.returncode == 0 else None
    if current and resolved != current:
        return (
            f"wired workflow ref '{ref}' ({resolved[:12]}) no longer matches the instance repo's "
            f"current default branch tip ({current[:12]})"
        )
    return None


def _panopticon_skill_files(root):
    """Map relative path -> absolute Path for every file under every ``panopticon-*`` directory
    directly beneath ``root`` (skills root only ever contains panopticon-owned skill directories
    among the ones this check cares about; other, org-owned skills are deliberately excluded)."""
    root = Path(root)
    files = {}
    if not root.is_dir():
        return files
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and entry.name.startswith("panopticon-"):
            for f in sorted(entry.rglob("*")):
                if f.is_file():
                    files[f.relative_to(root)] = f
    return files


def _tooling_module_files(root, modules):
    """Map relative path (``panopticon/<name>``) -> absolute Path for each vendored module that
    exists under ``root``."""
    files = {}
    for name in modules:
        f = Path(root) / "panopticon" / name
        if f.is_file():
            files[Path("panopticon") / name] = f
    return files


def _diff_files(instance_files, child_files):
    """Content-diff two relative-path -> Path maps (design D2: content, never timestamps).
    Returns one finding string per file that differs, is missing from the child, or is missing
    from the instance's current copy."""
    findings = []
    for rel in sorted(set(instance_files) | set(child_files), key=str):
        inst = instance_files.get(rel)
        child = child_files.get(rel)
        if inst is None:
            findings.append(f"{rel} exists in this repo but not in the instance's current copy")
        elif child is None:
            findings.append(f"{rel} is missing from this repo (the instance repo has it)")
        elif inst.read_bytes() != child.read_bytes():
            findings.append(f"{rel} is out of date (differs from the instance repo's current copy)")
    return findings


def check_skills_and_tooling_drift(child_root=".", instance_root=DEFAULT_INSTANCE_ROOT):
    """Skills/tooling drift check (design D2): plain recursive content diff between the instance
    checkout's ``panopticon-*`` skills and vendored local-tooling modules and the child repo's own
    copies. No new persisted config field: the child's skills location is re-derived the same way
    ``bootstrap.py``'s idempotent re-run already does."""
    from .bootstrap import DEFAULT_SKILLS_LOCATION, LOCAL_TOOLING_MODULES, SKILLS_PREFIX, _detect_existing_location

    child_location = _detect_existing_location(child_root) or DEFAULT_SKILLS_LOCATION

    instance_skills = _panopticon_skill_files(Path(instance_root) / SKILLS_PREFIX)
    child_skills = _panopticon_skill_files(Path(child_root) / child_location)

    instance_tooling = _tooling_module_files(instance_root, LOCAL_TOOLING_MODULES)
    child_tooling = _tooling_module_files(child_root, LOCAL_TOOLING_MODULES)

    return _diff_files(instance_skills, child_skills) + _diff_files(instance_tooling, child_tooling)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Advisory-only tooling-currency checks (CI only). Never gates; always exits 0."
    )
    parser.add_argument("--child-root", default=".")
    parser.add_argument("--instance-root", default=DEFAULT_INSTANCE_ROOT)
    args = parser.parse_args(argv)

    findings = []
    ref_finding = check_workflow_ref(args.child_root, args.instance_root)
    if ref_finding:
        findings.append(ref_finding)
    findings.extend(check_skills_and_tooling_drift(args.child_root, args.instance_root))

    if not findings:
        print(
            "Panopticon tooling-currency check: wired workflow ref, skills, and vendored tooling "
            "all match the instance repo's current default branch."
        )
    for finding in findings:
        print(f"::warning::Panopticon tooling-currency: {finding}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
