"""Index-currency check: verdict parsing, loud failures, report formatting."""

import json
import unittest
from pathlib import Path

from panopticon.currency import check_currency, format_report
from panopticon.llm import LLMResponseError

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


class TestReport(unittest.TestCase):
    def test_stale_report_names_updates(self):
        report = format_report(STALE_VERDICT)
        self.assertIn("stale for this change", report)
        self.assertIn("payment-retries", report)
        self.assertIn("panopticon-interface-extraction", report)

    def test_current_report(self):
        report = format_report({"current": True, "reasons": [], "summary": "ok"})
        self.assertIn("current", report)


if __name__ == "__main__":
    unittest.main()
