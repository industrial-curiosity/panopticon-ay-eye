"""Doc-drift check: verdict parsing, loud failures, report formatting."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from panopticon.drift import (
    DocDriftBatchError,
    MAX_DOC_BYTES,
    check_drift,
    collect_actions,
    collect_docs,
    format_report,
    format_batch_failure,
    main,
    validate_batches,
)
from panopticon.llm import LLMConfigurationError, LLMRequestError, LLMResponseError

from .test_extraction import FakeClient

REPO_ROOT = Path(__file__).resolve().parent.parent

STALE_VERDICT = {
    "stale": True,
    "reasons": [
        {
            "doc": "docs/components/api.md",
            "why": "New endpoint /v2/orders is not documented.",
            "update": "Document the /v2/orders endpoint.",
            "evidence": "src/api.py",
        }
    ],
    "summary": "API surface changed without a doc update.",
}


class TestCheckDrift(unittest.TestCase):
    behavior_diff = "diff --git a/src/api.py b/src/api.py\n+++ b/src/api.py\n+ new code"
    api_plan = json.dumps({"batches": [{"paths": ["src/api.py"], "docs": []}]})

    def test_verdict_round_trip_and_prompt_contents(self):
        client = FakeClient([self.api_plan, json.dumps(STALE_VERDICT)])
        verdict = check_drift(self.behavior_diff, {"docs/architecture.md": "# arch"}, client, skill_root=REPO_ROOT)
        self.assertTrue(verdict["stale"])
        self.assertEqual(verdict["reasons"], STALE_VERDICT["reasons"])
        skill_text, user_content = client.calls[1]
        self.assertIn("doc-drift verdict", skill_text)
        self.assertIn("src/api.py", user_content)
        self.assertIn("docs/architecture.md", client.calls[0][1])

    def test_malformed_verdict_fails_loudly(self):
        client = FakeClient([self.api_plan, "the docs look fine to me"])
        with self.assertRaises(LLMResponseError):
            check_drift(self.behavior_diff, {}, client, skill_root=REPO_ROOT)

    def test_missing_stale_field_fails_loudly(self):
        client = FakeClient([self.api_plan, json.dumps({"reasons": []})])
        with self.assertRaises(LLMResponseError):
            check_drift(self.behavior_diff, {}, client, skill_root=REPO_ROOT)

    def test_prose_first_response_recovers_on_retry(self):
        """Regression test for the real CI failure this change fixes: a model reasoning aloud
        ("Looking at this PR diff carefully...") instead of responding with JSON on the first
        attempt no longer crashes the check outright."""
        client = FakeClient([
            self.api_plan,
            "Looking at this PR diff carefully, I need to determine whether...",
            json.dumps(STALE_VERDICT),
        ])
        verdict = check_drift(self.behavior_diff, {"docs/architecture.md": "# arch"}, client, skill_root=REPO_ROOT)
        self.assertTrue(verdict["stale"])
        self.assertEqual(len(client.chat_calls), 3)

    def test_docs_skills_and_templates_change_without_llm_call(self):
        diff = """diff --git a/.agents/skills/panopticon-doc-generation/SKILL.md b/.agents/skills/panopticon-doc-generation/SKILL.md
+++ b/.agents/skills/panopticon-doc-generation/SKILL.md
+Use absolute links to the org diagram.
diff --git a/docs/architecture.md b/docs/architecture.md
+++ b/docs/architecture.md
+[org diagram](https://github.com/example/instance/blob/main/docs/architecture.md#child)
"""
        client = FakeClient(json.dumps(STALE_VERDICT))
        verdict = check_drift(diff, {"docs/architecture.md": "# arch"}, client, skill_root=REPO_ROOT)
        self.assertFalse(verdict["stale"])
        self.assertEqual(client.calls, [])

    def test_managed_metadata_only_diff_is_clean_without_llm_call(self):
        diff = """diff --git a/panopticon/drift.py b/panopticon/drift.py
+++ b/panopticon/drift.py
+metadata update
diff --git a/.github/workflows/panopticon-pr.yml b/.github/workflows/panopticon-pr.yml
+++ b/.github/workflows/panopticon-pr.yml
+workflow update
diff --git a/.agents/skills/panopticon-doc-drift/SKILL.md b/.agents/skills/panopticon-doc-drift/SKILL.md
+++ b/.agents/skills/panopticon-doc-drift/SKILL.md
+skill update
"""
        client = FakeClient(json.dumps(STALE_VERDICT))
        verdict = check_drift(diff, {}, client, skill_root=REPO_ROOT)
        self.assertFalse(verdict["stale"])
        self.assertEqual(client.calls, [])

    def test_illustrative_only_diff_is_clean_without_llm_call(self):
        diff = "diff --git a/demos/kafka.properties b/demos/kafka.properties\n+++ b/demos/kafka.properties\n+topic=demo"
        client = FakeClient(json.dumps(STALE_VERDICT))
        verdict = check_drift(diff, {}, client, skill_root=REPO_ROOT)
        self.assertFalse(verdict["stale"])
        self.assertEqual(client.calls, [])

    def test_file_hint_excludes_changed_file_without_llm_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "config.py").write_text("# panopticon-ignore file\nVALUE = 1\n")
            diff = "diff --git a/config.py b/config.py\n+++ b/config.py\n+VALUE = 1"
            client = FakeClient(json.dumps(STALE_VERDICT))
            verdict = check_drift(diff, {}, client, skill_root=REPO_ROOT, repo_root=tmp)
        self.assertFalse(verdict["stale"])
        self.assertEqual(client.calls, [])

    def test_targeted_context_includes_required_docs_and_matching_component_only(self):
        plan = json.dumps({"batches": [{"paths": ["src/api.py"], "docs": ["docs/components/api.md"]}]})
        client = FakeClient([plan, json.dumps({"stale": False, "reasons": [], "summary": "ok"})])
        client.request_diagnostic = {
            "provider": "litellm", "model": "m", "input_bytes": 1,
            "attempts": 1, "elapsed_seconds": 0.1, "outcome": "success",
        }
        docs = {
            "docs/architecture.md": "architecture",
            "docs/operations.md": "operations",
            "docs/interfaces.md": "rendered interface",
            "docs/components/api.md": "src/api.py",
            "docs/components/other.md": "src/other.py",
        }
        verdict = check_drift(self.behavior_diff, docs, client, skill_root=REPO_ROOT)
        content = client.calls[1][1]
        self.assertIn("docs/components/api.md", content)
        self.assertNotIn("docs/architecture.md", content)
        self.assertNotIn("docs/operations.md", content)
        self.assertNotIn("docs/interfaces.md", content)
        self.assertNotIn("docs/components/other.md", content)
        self.assertEqual(verdict["batches"][0]["docs"], ["docs/components/api.md"])

    def test_planner_can_select_multiple_relevant_documents(self):
        plan = json.dumps({"batches": [{"paths": ["src/api.py"], "docs": ["docs/components/api.md", "docs/components/other.md"]}]})
        client = FakeClient([plan, json.dumps({"stale": False, "reasons": [], "summary": "ok"})])
        client.request_diagnostic = None
        docs = {
            "docs/architecture.md": "architecture",
            "docs/components/api.md": "src/other.py",
            "docs/components/other.md": "src/another.py",
        }
        verdict = check_drift(self.behavior_diff, docs, client, skill_root=REPO_ROOT)
        content = client.calls[1][1]
        self.assertIn("docs/components/api.md", content)
        self.assertIn("docs/components/other.md", content)
        self.assertEqual(len(verdict["batches"]), 1)

    def test_planner_can_assign_no_documentation(self):
        client = FakeClient([self.api_plan, json.dumps({"stale": False, "reasons": [], "summary": "ok"})])
        client.request_diagnostic = None
        docs = {
            "docs/architecture.md": "a",
            "docs/components/first.md": "src/other.py\n" + ("x" * MAX_DOC_BYTES),
            "docs/components/second.md": "src/another.py\n" + ("y" * MAX_DOC_BYTES),
        }
        verdict = check_drift(self.behavior_diff, docs, client, skill_root=REPO_ROOT)
        self.assertEqual(verdict["batches"][0]["docs"], [])

    def test_deleted_behavior_file_is_evaluated(self):
        diff = "diff --git a/src/api.py b/src/api.py\n--- a/src/api.py\n+++ /dev/null\n- old code"
        verdict = check_drift(diff, {}, FakeClient([self.api_plan, json.dumps(STALE_VERDICT)]), skill_root=REPO_ROOT)
        self.assertTrue(verdict["stale"])

    def test_invalid_or_unsupported_stale_reasons_fail_loudly(self):
        invalid_verdicts = (
            {"stale": True, "reasons": [], "summary": "missing reason"},
            {"stale": True, "reasons": [{**STALE_VERDICT["reasons"][0], "update": "No update needed"}], "summary": "contradiction"},
            {"stale": True, "reasons": [{**STALE_VERDICT["reasons"][0], "evidence": "docs/architecture.md"}], "summary": "unsupported"},
        )
        for verdict in invalid_verdicts:
            with self.subTest(verdict=verdict):
                with self.assertRaises(LLMResponseError):
                    check_drift(self.behavior_diff, {}, FakeClient([self.api_plan, json.dumps(verdict)]), skill_root=REPO_ROOT)


class TestBatchPlanning(unittest.TestCase):
    def test_valid_batches_assign_each_changed_path_once(self):
        batches = validate_batches(
            {
                "batches": [
                    {"paths": ["src/api.py"], "docs": ["docs/components/api.md"]},
                    {"paths": ["src/worker.py"], "docs": []},
                ]
            },
            ["src/api.py", "src/worker.py"],
            {"docs/components/api.md": "# API"},
        )
        self.assertEqual(batches[0]["paths"], ["src/api.py"])
        self.assertEqual(batches[1]["docs"], [])

    def test_invalid_batches_are_rejected(self):
        cases = (
            (
                {"batches": [{"paths": ["src/api.py", "src/api.py"], "docs": []}]},
                "exactly once",
            ),
            (
                {"batches": [{"paths": ["src/api.py"], "docs": ["docs/missing.md"]}]},
                "unknown documentation path",
            ),
        )
        for plan, message in cases:
            with self.subTest(plan=plan):
                with self.assertRaisesRegex(ValueError, message):
                    validate_batches(plan, ["src/api.py"], {})

    def test_batches_are_evaluated_in_isolation_and_aggregated(self):
        diff = """diff --git a/src/api.py b/src/api.py
+++ b/src/api.py
+api change
diff --git a/src/worker.py b/src/worker.py
+++ b/src/worker.py
+worker change
"""
        plan = {
            "batches": [
                {"paths": ["src/api.py"], "docs": ["docs/components/api.md"]},
                {"paths": ["src/worker.py"], "docs": ["docs/components/worker.md"]},
            ]
        }
        stale = {**STALE_VERDICT, "reasons": [{**STALE_VERDICT["reasons"][0]}]}
        client = FakeClient([
            json.dumps(plan),
            json.dumps(stale),
            json.dumps({"stale": False, "reasons": [], "summary": "ok"}),
        ])
        verdict = check_drift(
            diff,
            {
                "docs/components/api.md": "# API",
                "docs/components/worker.md": "# Worker",
            },
            client,
            skill_root=REPO_ROOT,
        )
        self.assertTrue(verdict["stale"])
        self.assertEqual(verdict["reasons"], stale["reasons"])
        self.assertEqual(len(client.calls), 3)
        planner_content = client.calls[0][1]
        api_evaluator_content = client.calls[1][1]
        worker_evaluator_content = client.calls[2][1]
        self.assertNotIn("api change", planner_content)
        self.assertIn("api change", api_evaluator_content)
        self.assertNotIn("worker change", api_evaluator_content)
        self.assertIn("worker change", worker_evaluator_content)
        self.assertNotIn("api change", worker_evaluator_content)

    def test_timeout_recovery_output_is_stage_aware_and_secret_safe(self):
        error = DocDriftBatchError("evaluation", ["src/api.py"], RuntimeError("request timed out"))
        report = format_batch_failure(
            error,
            {
                "provider": "openai",
                "model": "gpt-test",
                "input_bytes": 42,
                "attempts": 3,
                "elapsed_seconds": 12.3,
                "outcome": "timeout",
                "endpoint": "https://secret.example",
                "token": "secret-value",
            },
        )
        self.assertIn("evaluation failed", report)
        self.assertIn("src/api.py", report)
        self.assertIn("input_bytes=42", report)
        self.assertIn("Reduce or split", report)
        self.assertIn("PANOPTICON_LLM_TIMEOUT_SECONDS", report)
        self.assertNotIn("secret.example", report)
        self.assertNotIn("secret-value", report)

    def test_evaluation_timeout_stops_before_later_batches(self):
        class TimeoutClient:
            def __init__(self):
                self.calls = 0

            def complete_json(self, *args, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return {
                        "batches": [
                            {"paths": ["src/api.py"], "docs": []},
                            {"paths": ["src/worker.py"], "docs": []},
                        ]
                    }
                raise LLMRequestError("https://provider.example", 2, TimeoutError("timed out"))

        diff = (
            "diff --git a/src/api.py b/src/api.py\n+++ b/src/api.py\n+api\n"
            "diff --git a/src/worker.py b/src/worker.py\n+++ b/src/worker.py\n+worker\n"
        )
        client = TimeoutClient()
        with self.assertRaisesRegex(DocDriftBatchError, "timed out") as raised:
            check_drift(diff, {}, client, skill_root=REPO_ROOT)
        self.assertEqual(raised.exception.stage, "evaluation")
        self.assertEqual(client.calls, 2)


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
                    "evidence": "src/topics.py",
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

    def test_report_includes_each_batch_diagnostic(self):
        report = format_report(
            {
                "stale": False,
                "reasons": [],
                "summary": "ok",
                "batch_diagnostics": [
                    {
                        "paths": ["src/api.py"],
                        "diagnostic": {
                            "provider": "openai",
                            "model": "gpt-test",
                            "input_bytes": 12,
                            "attempts": 1,
                            "elapsed_seconds": 0.1,
                            "outcome": "success",
                        },
                    }
                ],
            }
        )
        self.assertIn("src/api.py", report)
        self.assertIn("input_bytes=12", report)


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
                {"doc": "docs/architecture.md", "why": "x", "update": "y", "evidence": "src/a.py"},
                {"doc": "docs/interfaces.md", "why": "missing entries", "update": "add them", "evidence": "src/b.py"},
                {"doc": "docs/operations.md", "why": "x", "update": "y", "evidence": "src/c.py"},
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
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(argv)
            self.last_stdout = output.getvalue()
            return code

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
        self.assertIn("Panopticon doc-drift check could not run", self.last_stdout)

    def test_invalid_llm_configuration_is_an_operational_failure(self):
        def raise_configuration_error(*args, **kwargs):
            raise LLMConfigurationError("invalid PANOPTICON_LLM_TIMEOUT_SECONDS")

        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_main(Path(tmp), raise_configuration_error)
        self.assertNotIn(code, (0, 2))
        self.assertIn("invalid PANOPTICON_LLM_TIMEOUT_SECONDS", self.last_stdout)

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
