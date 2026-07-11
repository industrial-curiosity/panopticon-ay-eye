"""Diagram-existence PR check: report formatting, collect_actions, main()'s exit-code contract.

Deterministic, no LLM — unlike drift.py/currency.py this check needs no client stub. Same
exit-code contract: 0=well-formed, 2=missing/malformed, anything else=operational failure (an
unsupported configured format, per config.require_supported_diagram_format)."""

import json
import tempfile
import unittest
from pathlib import Path

from panopticon.diagram_check import collect_actions, format_report, main


class TestFormatReport(unittest.TestCase):
    def test_no_problems_is_a_pass(self):
        self.assertIn("present and well-formed", format_report([]))

    def test_problems_are_listed_with_remediation(self):
        report = format_report(["architecture diagram section missing: no heading"])
        self.assertIn("missing or malformed", report)
        self.assertIn("no heading", report)
        self.assertIn("panopticon-doc-generation", report)


class TestCollectActions(unittest.TestCase):
    def test_no_problems_has_no_actions(self):
        self.assertEqual(collect_actions([]), [])

    def test_problems_yield_run_doc_generation_and_commit_push(self):
        self.assertEqual(
            collect_actions(["missing"]),
            [{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}],
        )


class TestMainExitCodes(unittest.TestCase):
    def _run(self, tmp, architecture_md_text, diagram_config=None, report_file=None, actions_file=None):
        docs = tmp / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text(architecture_md_text)
        if diagram_config is not None:
            (tmp / "panopticon.diagram.config.json").write_text(json.dumps(diagram_config))
        argv = ["--docs-root", str(docs), "--instance-root", str(tmp)]
        if report_file:
            argv += ["--report-file", str(report_file)]
        if actions_file:
            argv += ["--actions-file", str(actions_file)]
        return main(argv)

    def test_well_formed_section_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run(Path(tmp), "# x\n\n## Architecture diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n")
        self.assertEqual(code, 0)

    def test_missing_section_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run(Path(tmp), "# x\n\nno diagram\n")
        self.assertEqual(code, 2)

    def test_unsupported_format_exits_neither_zero_nor_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run(
                Path(tmp), "# x\n\n## Architecture diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n",
                diagram_config={"format": "plantuml"},
            )
        self.assertNotIn(code, (0, 2))

    def test_unsupported_format_writes_could_not_run_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_file = tmp_path / "diagram.md"
            self._run(
                tmp_path, "# x\n\n## Architecture diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n",
                diagram_config={"format": "plantuml"}, report_file=report_file,
            )
            text = report_file.read_text()
        self.assertIn("could not run", text)

    def test_configured_format_is_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run(
                Path(tmp), "# x\n\n## Architecture diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n",
                diagram_config={"format": "mermaid"},
            )
        self.assertEqual(code, 0)

    def test_missing_writes_actions_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            actions_file = tmp_path / "actions.json"
            self._run(tmp_path, "# x\n\nno diagram\n", actions_file=actions_file)
            actions = json.loads(actions_file.read_text())
        self.assertEqual(actions, [{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}])


if __name__ == "__main__":
    unittest.main()
