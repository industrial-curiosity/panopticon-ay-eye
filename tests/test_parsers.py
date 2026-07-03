"""Starter parsers: detection and extraction over the sample repo fixture."""

import unittest

from panopticon.parsers import detecting_parsers, kafka_topics, rest_openapi, run_parsers

from .helpers import SAMPLE_REPO


class TestRegistry(unittest.TestCase):
    def test_both_starter_parsers_detect_sample_repo(self):
        self.assertEqual(sorted(detecting_parsers(SAMPLE_REPO)), ["kafka", "rest"])

    def test_run_parsers_groups_by_type(self):
        results = run_parsers(SAMPLE_REPO)
        self.assertEqual(sorted(results), ["kafka", "rest"])
        for candidates in results.values():
            self.assertTrue(candidates)


class TestRestOpenapi(unittest.TestCase):
    def test_extracts_json_spec_title(self):
        candidates = rest_openapi.extract(SAMPLE_REPO)
        by_file = {c["source_file"]: c for c in candidates}
        spec = by_file["api/openapi.json"]
        self.assertEqual(spec["raw_name"], "Orders API")
        self.assertEqual(spec["role"], "producer")
        self.assertTrue(spec["owned"])
        self.assertIsNone(spec["hint"])

    def test_yaml_spec_hint_pins_name(self):
        candidates = rest_openapi.extract(SAMPLE_REPO)
        by_file = {c["source_file"]: c for c in candidates}
        spec = by_file["api/openapi-billing.yaml"]
        self.assertEqual(spec["raw_name"], "Billing Service HTTP API")
        self.assertEqual(spec["hint"], "billing-api")


class TestKafkaTopics(unittest.TestCase):
    def setUp(self):
        self.by_key = {}
        for candidate in kafka_topics.extract(SAMPLE_REPO):
            self.by_key[(candidate["source_file"], candidate["raw_name"])] = candidate

    def test_properties_reference_is_consumer_with_hint(self):
        candidate = self.by_key[("config/kafka.properties", "order.events")]
        self.assertEqual(candidate["role"], "consumer")
        self.assertFalse(candidate["owned"])
        self.assertEqual(candidate["hint"], "order-events")

    def test_json_creation_config_is_owned_producer(self):
        candidate = self.by_key[("config/kafka-topics.json", "order.events")]
        self.assertEqual(candidate["role"], "producer")
        self.assertTrue(candidate["owned"])

    def test_json_bare_reference_is_consumer(self):
        candidate = self.by_key[("config/kafka-topics.json", "billing-events")]
        self.assertEqual(candidate["role"], "consumer")
        self.assertFalse(candidate["owned"])

    def test_yaml_creation_config_with_hint(self):
        candidate = self.by_key[("config/topics.yaml", "audit_log.events")]
        self.assertEqual(candidate["role"], "producer")
        self.assertTrue(candidate["owned"])
        self.assertEqual(candidate["hint"], "audit-log-events")

    def test_yaml_topic_reference_is_consumer(self):
        candidate = self.by_key[("config/topics.yaml", "billing-events")]
        self.assertEqual(candidate["role"], "consumer")


if __name__ == "__main__":
    unittest.main()
