"""Validate declared caller inputs and secrets in reusable GitHub Actions workflows.

The source scanner intentionally supports Panopticon's stable provider-workflow
shape only: ``on.workflow_call.inputs`` and ``on.workflow_call.secrets`` maps,
plus dot-form ``inputs.name`` and ``secrets.name`` GitHub expressions. It avoids
a YAML dependency because GitHub Actions has YAML-specific semantics, including
the unquoted ``on`` key.
"""

import argparse
import re
import sys
from pathlib import Path


_MAPPING_KEY = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_-]*):\s*(?:#.*)?$")
_EXPRESSION = re.compile(r"\$\{\{(?P<body>.*?)\}\}")
_REFERENCE = re.compile(r"\b(?P<kind>inputs|secrets)\.(?P<name>[A-Za-z_][A-Za-z0-9_-]*)\b")


def _mapping_key(line):
    """Return a plain YAML mapping key and its indentation, or ``None``."""
    match = _MAPPING_KEY.match(line)
    if match is None:
        return None
    return len(match.group("indent")), match.group("key")


def _child_mapping(lines, parent_index, parent_indent, name):
    """Find ``name`` as a direct mapping child, returning its line and indent."""
    for index in range(parent_index + 1, len(lines)):
        mapping = _mapping_key(lines[index])
        if mapping is None:
            continue
        indent, key = mapping
        if indent <= parent_indent:
            return None
        if indent > parent_indent and key == name:
            return index, indent
    return None


def _mapping_keys(lines, parent_index, parent_indent):
    """Return direct child keys from a mapping block in the supported workflow shape."""
    keys = set()
    child_indent = None
    for index in range(parent_index + 1, len(lines)):
        mapping = _mapping_key(lines[index])
        if mapping is None:
            continue
        indent, key = mapping
        if indent <= parent_indent:
            break
        if child_indent is None:
            child_indent = indent
        if indent == child_indent:
            keys.add(key)
    return keys


def declared_values(text):
    """Return declared ``inputs`` and ``secrets`` names from a reusable workflow."""
    lines = text.splitlines()
    root = next(
        ((index, mapping[0]) for index, line in enumerate(lines)
         if (mapping := _mapping_key(line)) and mapping[1] == "on" and mapping[0] == 0),
        None,
    )
    if root is None:
        return {"inputs": set(), "secrets": set()}
    workflow_call = _child_mapping(lines, root[0], root[1], "workflow_call")
    if workflow_call is None:
        return {"inputs": set(), "secrets": set()}
    declared = {}
    for kind in ("inputs", "secrets"):
        mapping = _child_mapping(lines, workflow_call[0], workflow_call[1], kind)
        declared[kind] = set() if mapping is None else _mapping_keys(lines, *mapping)
    return declared


def is_reusable_workflow(text):
    """Return whether ``text`` declares a root-level ``on.workflow_call`` contract."""
    lines = text.splitlines()
    root = next(
        ((index, mapping[0]) for index, line in enumerate(lines)
         if (mapping := _mapping_key(line)) and mapping[1] == "on" and mapping[0] == 0),
        None,
    )
    return root is not None and _child_mapping(lines, root[0], root[1], "workflow_call") is not None


def reusable_workflows(workflows_dir):
    """Return shipped reusable workflow paths in deterministic order."""
    workflows_dir = Path(workflows_dir)
    paths = sorted({*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")})
    return tuple(
        path for path in paths
        if is_reusable_workflow(path.read_text(encoding="utf-8"))
    )


def referenced_values(text):
    """Return dot-form caller values referenced by GitHub expressions in ``text``."""
    references = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for expression in _EXPRESSION.finditer(line):
            for match in _REFERENCE.finditer(expression.group("body")):
                references.add((match.group("kind"), match.group("name")))
    return references


def undeclared_references(text):
    """Return stable ``kind.name`` errors for caller values lacking declarations."""
    declared = declared_values(text)
    return tuple(
        f"{kind}.{name}"
        for kind, name in sorted(referenced_values(text))
        if name not in declared[kind]
    )


def validate_workflow(path):
    """Return undeclared caller-value references found in the workflow at ``path``."""
    return undeclared_references(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate reusable-workflow caller input and secret references."
    )
    parser.add_argument("workflows", nargs="*", type=Path)
    parser.add_argument(
        "--workflows-dir", type=Path,
        help="discover and validate reusable workflows in this directory",
    )
    args = parser.parse_args(argv)
    workflows = list(args.workflows)
    if args.workflows_dir is not None:
        workflows.extend(reusable_workflows(args.workflows_dir))
    if not workflows:
        parser.error("provide workflow paths or --workflows-dir")

    errors = []
    for path in sorted(set(workflows)):
        for reference in validate_workflow(path):
            errors.append(f"{path}: undeclared workflow_call {reference}")
    if errors:
        print("\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
