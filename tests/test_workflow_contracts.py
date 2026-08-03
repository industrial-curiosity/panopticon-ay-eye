"""Contract validation for template-owned reusable provider workflows."""

import contextlib
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from panopticon.workflow_contracts import (
    main,
    reusable_workflows,
    undeclared_references,
    validate_workflow,
)


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"


class TestWorkflowContracts(unittest.TestCase):
    def test_shipped_provider_workflows_declare_every_referenced_caller_value(self):
        for provider in ("litellm", "openai", "bedrock"):
            with self.subTest(provider=provider):
                self.assertEqual(
                    validate_workflow(WORKFLOWS / f"panopticon-pr-{provider}.yml"),
                    (),
                )

    def test_undeclared_input_and_secret_are_reported_in_stable_order(self):
        text = """on:
  workflow_call:
    inputs:
      model:
        required: true
        type: string
    secrets:
      instance_token:
        required: true
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo ${{ inputs.endpoint }} ${{ secrets.api_key }} ${{ inputs.model }}
"""
        self.assertEqual(
            undeclared_references(text),
            ("inputs.endpoint", "secrets.api_key"),
        )

    def test_cli_returns_nonzero_and_names_the_invalid_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "invalid.yml"
            workflow.write_text(
                "on:\n  workflow_call:\n    inputs:\n      model:\n        type: string\n"
                "jobs:\n  check:\n    runs-on: ubuntu-latest\n"
                "    steps:\n      - run: echo ${{ inputs.endpoint }}\n",
                encoding="utf-8",
            )
            output = StringIO()
            with contextlib.redirect_stdout(output):
                result = main([str(workflow)])
        self.assertEqual(result, 1)
        self.assertIn("undeclared workflow_call inputs.endpoint", output.getvalue())

    def test_reusable_workflow_discovery_selects_only_workflow_call_files(self):
        reusable = "on:\n  workflow_call:\n    inputs: {}\n"
        non_reusable = "on:\n  pull_request:\n"
        with tempfile.TemporaryDirectory() as tmp:
            workflows = Path(tmp)
            (workflows / "provider.yml").write_text(reusable, encoding="utf-8")
            (workflows / "push.yaml").write_text(non_reusable, encoding="utf-8")
            discovered = reusable_workflows(workflows)
        self.assertEqual(tuple(path.name for path in discovered), ("provider.yml",))

    def test_reusable_workflow_discovery_finds_every_shipped_contract(self):
        self.assertEqual(
            tuple(path.name for path in reusable_workflows(WORKFLOWS)),
            (
                "panopticon-merge.yml",
                "panopticon-pr-bedrock.yml",
                "panopticon-pr-close.yml",
                "panopticon-pr-litellm.yml",
                "panopticon-pr-openai.yml",
                "panopticon-pr.yml",
                "shared-child-resource-sync.yml",
                "shared-template-sync-caller-only.yml",
            ),
        )

    def test_cli_discovery_validates_all_reusable_workflows(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflows = Path(tmp)
            (workflows / "valid.yml").write_text(
                "on:\n  workflow_call:\n    inputs:\n      model:\n        type: string\n",
                encoding="utf-8",
            )
            (workflows / "invalid.yaml").write_text(
                "on:\n  workflow_call:\n    inputs: {}\njobs:\n  check:\n"
                "    runs-on: ubuntu-latest\n    steps:\n"
                "      - run: echo ${{ inputs.model }}\n",
                encoding="utf-8",
            )
            (workflows / "push.yml").write_text(
                "on:\n  push:\n", encoding="utf-8"
            )
            output = StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--workflows-dir", str(workflows)])
        self.assertEqual(result, 1)
        self.assertIn("invalid.yaml", output.getvalue())
        self.assertNotIn("push.yml", output.getvalue())

    def test_template_validation_workflow_runs_discovery_and_test_suite(self):
        workflow = (WORKFLOWS / "template-validation.yml").read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("python3 -m panopticon.workflow_contracts --workflows-dir .github/workflows", workflow)
        self.assertIn("python3 -m unittest discover -t . -s tests", workflow)


if __name__ == "__main__":
    unittest.main()
