"""Extraction driver: parser folding, LLM fallback tagging, parser-gap recommendations."""

import json
import unittest
from pathlib import Path

from panopticon.index import KIND_LOCAL, validate_index
from panopticon.llm import LLMClient, LLMResponseError
from panopticon.naming import UnresolvableNameError
from panopticon.extraction import (
    candidates_to_index,
    extract_repo,
    fallback_candidate_files,
    llm_extract,
    parser_gap_recommendations,
)

from .helpers import SAMPLE_REPO

REPO_ROOT = Path(__file__).resolve().parent.parent


class FakeClient:
    """Stands in for LLMClient. `response` is a single canned completion (repeated on every
    `chat()` call, matching the old behavior) or a list of completions consumed in order — the
    last one repeats once exhausted, mirroring `test_llm.py`'s `StubLLMServer` convention, so
    retry-then-succeed and retry-exhausted scenarios can be exercised.

    `complete_with_skill`/`complete_json` delegate to the real `LLMClient` implementations bound
    to this fake (only `chat()`, the transport, is faked) — so tests exercise the actual
    retry/parse/validate logic, never a duplicated reimplementation of it."""

    def __init__(self, response):
        self.responses = [response] if isinstance(response, str) else list(response)
        self.calls = []       # (skill_text, user_content) — one entry per top-level invocation
        self.chat_calls = []  # every underlying chat() call's messages list, in order

    def chat(self, messages, temperature=0):
        self.chat_calls.append(messages)
        idx = min(len(self.chat_calls), len(self.responses)) - 1
        return self.responses[idx]

    def complete_with_skill(self, skill_text, user_content, temperature=0):
        self.calls.append((skill_text, user_content))
        return LLMClient.complete_with_skill(self, skill_text, user_content, temperature=temperature)

    def complete_json(self, skill_text, user_content, validate, *, response_label,
                       expected_shape="object", temperature=0, max_correction_attempts=2):
        self.calls.append((skill_text, user_content))
        return LLMClient.complete_json(
            self, skill_text, user_content, validate, response_label=response_label,
            expected_shape=expected_shape, temperature=temperature,
            max_correction_attempts=max_correction_attempts,
        )


class TestCandidatesToIndex(unittest.TestCase):
    def test_sample_repo_parsers_produce_valid_local_index(self):
        doc, summary = extract_repo(SAMPLE_REPO, "svc-x")
        validate_index(doc, kind=KIND_LOCAL, repo="svc-x")
        self.assertEqual(summary, [])
        # hint + normalization converge declaring and referencing files on one canonical entry
        (entry,) = doc["interfaces"]["order-events"]
        self.assertEqual(entry["type"], "kafka")
        self.assertEqual(entry["owner"], {"repo": "svc-x", "component": "svc-x"})
        self.assertEqual(entry["producer"][0]["source_files"], ["config/kafka-topics.json"])
        self.assertEqual(entry["consumer"][0]["source_files"], ["config/kafka.properties"])
        self.assertIn("billing-api", doc["interfaces"])
        self.assertIn("orders-api", doc["interfaces"])

    def test_unresolvable_name_fails_with_hint_instruction(self):
        candidates = [
            {
                "raw_name": "---",
                "hint": None,
                "type": "kafka",
                "role": "consumer",
                "source_file": "config/x.properties",
                "owned": False,
                "component": None,
            }
        ]
        with self.assertRaises(UnresolvableNameError) as ctx:
            candidates_to_index(candidates, "svc-x")
        self.assertIn("panopticon-interface", str(ctx.exception))


class TestFallbackSelection(unittest.TestCase):
    def test_covered_and_oversized_files_are_excluded(self):
        covered = {"config/kafka-topics.json", "config/kafka.properties", "config/topics.yaml"}
        files = fallback_candidate_files(SAMPLE_REPO, covered)
        self.assertIn("api/openapi.json", files)
        self.assertNotIn("config/kafka-topics.json", files)

    def test_ci_mode_restricts_to_changed_files(self):
        files = fallback_candidate_files(SAMPLE_REPO, set(), changed_files=["config/topics.yaml"])
        self.assertEqual(files, ["config/topics.yaml"])


class TestLLMFallback(unittest.TestCase):
    def llm_candidates(self):
        return [
            {
                "raw_name": "invoice_queue",
                "hint": None,
                "type": "sqs",
                "role": "consumer",
                "owned": False,
                "component": None,
                "source_file": "config/queues.json",
            }
        ]

    def test_entries_are_tagged_and_gap_reported(self):
        client = FakeClient(json.dumps(self.llm_candidates()))
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["extracted_by"], "llm")
        doc = candidates_to_index(candidates, "svc-x")
        self.assertEqual(doc["interfaces"]["invoice-queue"][0]["extracted_by"], "llm")
        (recommendation,) = parser_gap_recommendations(candidates)
        self.assertIn("'sqs'", recommendation)
        self.assertIn("deterministic parser", recommendation)

    def test_skill_is_loaded_as_system_prompt(self):
        client = FakeClient("[]")
        llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        skill_text, user_content = client.calls[0]
        self.assertIn("Response contract", skill_text)
        self.assertIn("config/topics.yaml", user_content)

    def test_no_candidate_files_makes_no_call(self):
        client = FakeClient("[]")
        self.assertEqual(llm_extract(client, SAMPLE_REPO, [], skill_root=REPO_ROOT), [])
        self.assertEqual(client.calls, [])

    def test_malformed_response_fails_loudly(self):
        client = FakeClient("I found some interfaces!")
        with self.assertRaises(LLMResponseError):
            llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)

    def test_prose_first_response_recovers_on_retry(self):
        client = FakeClient([
            "Looking at these files, I can identify the following interfaces...",
            json.dumps(self.llm_candidates()),
        ])
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["raw_name"], "invoice_queue")
        self.assertEqual(len(client.chat_calls), 2)

    def test_item_missing_required_field_recovers_on_retry(self):
        """Previously: a malformed item crashed with an uncaught KeyError outside any
        try/except. Now shape-validated the same way as a top-level parse failure."""
        malformed = [{"type": "sqs", "source_file": "config/queues.json"}]  # raw_name missing
        client = FakeClient([json.dumps(malformed), json.dumps(self.llm_candidates())])
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["raw_name"], "invoice_queue")
        self.assertEqual(len(client.chat_calls), 2)

    def test_item_missing_field_eventually_fails_loudly(self):
        malformed = [{"type": "sqs", "source_file": "config/queues.json"}]
        client = FakeClient(json.dumps(malformed))
        with self.assertRaises(LLMResponseError):
            llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)

    def test_code_fenced_response_is_accepted(self):
        client = FakeClient("```json\n" + json.dumps(self.llm_candidates()) + "\n```")
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["raw_name"], "invoice_queue")


if __name__ == "__main__":
    unittest.main()
