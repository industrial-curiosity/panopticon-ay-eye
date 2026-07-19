"""Index-currency check: verdict parsing, loud failures, report formatting."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from panopticon.currency import check_currency, collect_actions, format_report, main
from panopticon.index import dumps_index
from panopticon.llm import LLMConfigurationError, LLMResponseError

from .helpers import load_fixture
from .test_extraction import FakeClient

REPO_ROOT = Path(__file__).resolve().parent.parent

STALE_VERDICT = {
    "current": False,
    "reasons": [
        {
            "what": "New Kafka topic 'payment.retries' has no index entry.",
            "index_update": "Add a 'payment-retries' (kafka) entry with this repo as producer.",
        }
    ],
    "summary": "New topic missing from the local index.",
}


class TestCheckCurrency(unittest.TestCase):
    def test_verdict_round_trip_and_prompt_contents(self):
        client = FakeClient(json.dumps(STALE_VERDICT))
        index_doc = load_fixture("local_svc_a.json")
        verdict = check_currency("+ topic config", index_doc, client, skill_root=REPO_ROOT)
        self.assertEqual(verdict, STALE_VERDICT)
        skill_text, user_content = client.calls[0]
        self.assertIn("index-currency verdict", skill_text)
        self.assertIn("+ topic config", user_content)
        self.assertIn("order-events", user_content)

    def test_malformed_verdict_fails_loudly(self):
        client = FakeClient("index looks fine")
        with self.assertRaises(LLMResponseError):
            check_currency("diff", load_fixture("local_svc_a.json"), client, skill_root=REPO_ROOT)

    def test_prose_first_response_recovers_on_retry(self):
        client = FakeClient([
            "Let me examine the diff and the index to figure out...",
            json.dumps(STALE_VERDICT),
        ])
        verdict = check_currency(
            "+ topic config", load_fixture("local_svc_a.json"), client, skill_root=REPO_ROOT
        )
        self.assertEqual(verdict, STALE_VERDICT)
        self.assertEqual(len(client.chat_calls), 2)


class TestReport(unittest.TestCase):
    def test_stale_report_names_updates(self):
        report = format_report(STALE_VERDICT)
        self.assertIn("stale for this change", report)
        self.assertIn("payment-retries", report)
        self.assertIn("panopticon-interface-extraction", report)

    def test_current_report(self):
        report = format_report({"current": True, "reasons": [], "summary": "ok"})
        self.assertIn("current", report)


class TestCollectActions(unittest.TestCase):
    def test_current_verdict_has_no_actions(self):
        self.assertEqual(collect_actions({"current": True, "reasons": [], "summary": "ok"}), [])

    def test_stale_verdict_yields_run_doc_generation_and_commit_push(self):
        self.assertEqual(
            collect_actions(STALE_VERDICT),
            [{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}],
        )


class TestMainExitCodes(unittest.TestCase):
    """Exit-code contract (pr-evaluation spec: "CI checks distinguish operational failure from a
    business verdict by exit code"): 0=current, 2=stale, anything else=operational failure — 1 must
    never mean "stale", since that's the code an uncaught exception would produce anyway."""

    def _run_main(self, tmp, check_currency_result, report_file=None):
        diff_file = tmp / "diff.txt"
        diff_file.write_text("+ change")
        index_file = tmp / "index.json"
        index_file.write_text(dumps_index(load_fixture("local_svc_a.json")))
        effect = (
            check_currency_result if callable(check_currency_result)
            else lambda *a, **k: check_currency_result
        )
        argv = ["--diff-file", str(diff_file), "--index", str(index_file), "--repo", "svc-a"]
        if report_file:
            argv += ["--report-file", str(report_file)]
        with patch("panopticon.currency.LLMClient.from_env", return_value=None), \
             patch("panopticon.currency.check_currency", side_effect=effect):
            return main(argv)

    def test_current_verdict_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_main(Path(tmp), {"current": True, "reasons": [], "summary": "ok"})
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

    def test_invalid_llm_configuration_is_an_operational_failure(self):
        def raise_configuration_error(*args, **kwargs):
            raise LLMConfigurationError("invalid PANOPTICON_LLM_TIMEOUT_SECONDS")

        with tempfile.TemporaryDirectory() as tmp:
            code = self._run_main(Path(tmp), raise_configuration_error)
        self.assertNotIn(code, (0, 2))

    def test_operational_failure_writes_failure_section_to_report_file(self):
        def raise_response_error(*args, **kwargs):
            raise LLMResponseError("endpoint returned garbage")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_file = tmp_path / "currency.md"
            self._run_main(tmp_path, raise_response_error, report_file=report_file)
            text = report_file.read_text()
        self.assertIn("could not run", text)
        self.assertIn("endpoint returned garbage", text)


if __name__ == "__main__":
    unittest.main()
