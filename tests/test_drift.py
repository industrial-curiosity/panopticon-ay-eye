"""Doc-drift check: verdict parsing, loud failures, report formatting."""

import json
import unittest
from pathlib import Path

from panopticon.drift import check_drift, collect_actions, collect_docs, format_report
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
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            (docs / "components").mkdir(parents=True)
            (docs / "architecture.md").write_text("# arch")
            (docs / "components" / "api.md").write_text("# api")
            collected = collect_docs(docs)
        self.assertEqual(sorted(collected), ["docs/architecture.md", "docs/components/api.md"])


if __name__ == "__main__":
    unittest.main()
