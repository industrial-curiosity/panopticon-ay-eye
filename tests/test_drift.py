"""Doc-drift check: verdict parsing, loud failures, report formatting."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from panopticon.drift import check_drift, collect_actions, collect_docs, format_report, main
from panopticon.llm import LLMResponseError

from .test_extraction import FakeClient

REPO_ROOT = Path(__file__).resolve().parent.parent

STALE_VERDICT = {
    "stale": True,
    "reasons": [
        {
            "doc": "docs/components/api.md",
            "why": "New endpoint /v2/orders is not documented.",
            "update": "Document the /v2/orders endpoint.",
        }
    ],
    "summary": "API surface changed without a doc update.",
}


class TestCheckDrift(unittest.TestCase):
    def test_verdict_round_trip_and_prompt_contents(self):
        client = FakeClient(json.dumps(STALE_VERDICT))
        verdict = check_drift("+ new code", {"docs/architecture.md": "# arch"}, client, skill_root=REPO_ROOT)
        self.assertEqual(verdict, STALE_VERDICT)
        skill_text, user_content = client.calls[0]
        self.assertIn("doc-drift verdict", skill_text)
        self.assertIn("+ new code", user_content)
        self.assertIn("docs/architecture.md", user_content)

    def test_malformed_verdict_fails_loudly(self):
        client = FakeClient("the docs look fine to me")
        with self.assertRaises(LLMResponseError):
            check_drift("diff", {}, client, skill_root=REPO_ROOT)

    def test_missing_stale_field_fails_loudly(self):
        client = FakeClient(json.dumps({"reasons": []}))
        with self.assertRaises(LLMResponseError):
            check_drift("diff", {}, client, skill_root=REPO_ROOT)

    def test_prose_first_response_recovers_on_retry(self):
        """Regression test for the real CI failure this change fixes: a model reasoning aloud
        ("Looking at this PR diff carefully...") instead of responding with JSON on the first
        attempt no longer crashes the check outright."""
        client = FakeClient([
            "Looking at this PR diff carefully, I need to determine whether...",
            json.dumps(STALE_VERDICT),
        ])
        verdict = check_drift("+ new code", {"docs/architecture.md": "# arch"}, client, skill_root=REPO_ROOT)
        self.assertEqual(verdict, STALE_VERDICT)
        self.assertEqual(len(client.chat_calls), 2)


class TestReport(unittest.TestCase):
    def test_stale_report_names_docs_and_remediation(self):
        report = format_report(STALE_VERDICT)
        self.assertIn("documentation updates required", report)
        self.assertIn("docs/components/api.md", report)
        self.assertIn("What to update", report)
        self.assertIn("panopticon-doc-generation", report)

    def test_stale_report_states_same_branch_push_and_rerun(self):
        report = format_report(STALE_VERDICT)
        self.assertIn("this same PR's branch", report)
        self.assertIn("do not open a new pr", report.lower())
        self.assertIn("re-runs automatically", report)

    def test_stale_report_gives_interface_doc_specific_remediation(self):
        verdict = {
            "stale": True,
            "reasons": [
                {
                    "doc": "docs/interfaces.md",
                    "why": "New Kafka topic is not reflected in the interface index.",
                    "update": "Add the topic to panopticon/index.json.",
                }
            ],
            "summary": "Interface index changed without updating interfaces.md.",
        }
        report = format_report(verdict)
        self.assertIn("python3 -m panopticon.docs render", report)
        self.assertIn("panopticon/index.json", report)
        # interfaces.md is rendered, not agent-authored — it must not get the generic agent-skill fix line
        self.assertNotIn("run the panopticon-doc-generation skill", report)

    def test_clean_report(self):
        report = format_report({"stale": False, "reasons": [], "summary": "ok"})
        self.assertIn("consistent", report)


class TestCollectActions(unittest.TestCase):
    def test_clean_verdict_has_no_actions(self):
        self.assertEqual(collect_actions({"stale": False, "reasons": [], "summary": "ok"}), [])

    def test_stale_verdict_yields_run_doc_generation_and_commit_push(self):
        self.assertEqual(
            collect_actions(STALE_VERDICT),
            [{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}],
        )

    def test_many_stale_docs_including_interfaces_still_yield_one_action(self):
        # No matter how many docs are stale, or whether interfaces.md is among them, it's one action.
        verdict = {
            "stale": True,
            "reasons": [
                {"doc": "docs/architecture.md", "why": "x", "update": "y"},
                {"doc": "docs/interfaces.md", "why": "missing entries", "update": "add them"},
                {"doc": "docs/operations.md", "why": "x", "update": "y"},
            ],
            "summary": "several docs stale",
        }
        self.assertEqual(
            collect_actions(verdict),
            [{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}],
        )


class TestCollectDocs(unittest.TestCase):
    def test_collects_markdown_relative_to_docs_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            (docs / "components").mkdir(parents=True)
            (docs / "architecture.md").write_text("# arch")
            (docs / "components" / "api.md").write_text("# api")
            collected = collect_docs(docs)
        self.assertEqual(sorted(collected), ["docs/architecture.md", "docs/components/api.md"])


class TestMainExitCodes(unittest.TestCase):
    """Exit-code contract (pr-evaluation spec: "CI checks distinguish operational failure from a
    business verdict by exit code"): 0=clean, 2=stale, anything else=operational failure — 1 must
    never mean "stale", since that's the code an uncaught exception would produce anyway."""

    def _run_main(self, tmp, check_drift_result, report_file=None):
        diff_file = tmp / "diff.txt"
        diff_file.write_text("+ change")
        docs_root = tmp / "docs"
        docs_root.mkdir()
        effect = check_drift_result if callable(check_drift_result) else lambda *a, **k: check_drift_result
        argv = ["--diff-file", str(diff_file), "--docs-root", str(docs_root)]
        if report_file:
            argv += ["--report-file", str(report_file)]
        with patch("panopticon.drift.LLMClient.from_env", return_value=None), \
             patch("panopticon.drift.check_drift", side_effect=effect):
            return main(argv)

    def test_clean_verdict_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_main(Path(tmp), {"stale": False, "reasons": [], "summary": "ok"})
        self.assertEqual(code, 0)

    def test_stale_verdict_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_main(Path(tmp), STALE_VERDICT)
        self.assertEqual(code, 2)

    def test_operational_failure_exits_neither_zero_nor_two(self):
        def raise_response_error(*args, **kwargs):
            raise LLMResponseError("endpoint returned garbage")

        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_main(Path(tmp), raise_response_error)
        self.assertNotIn(code, (0, 2))

    def test_operational_failure_writes_failure_section_to_report_file(self):
        def raise_response_error(*args, **kwargs):
            raise LLMResponseError("endpoint returned garbage")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_file = tmp_path / "drift.md"
            self._run_main(tmp_path, raise_response_error, report_file=report_file)
            text = report_file.read_text()
        self.assertIn("could not run", text)
        self.assertIn("endpoint returned garbage", text)
        self.assertNotIn("stale", text.lower())


if __name__ == "__main__":
    unittest.main()
