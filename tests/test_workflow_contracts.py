"""Contract validation for template-owned reusable provider workflows."""

import contextlib
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from panopticon.workflow_contracts import main, undeclared_references, validate_workflow


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


if __name__ == "__main__":
    unittest.main()
