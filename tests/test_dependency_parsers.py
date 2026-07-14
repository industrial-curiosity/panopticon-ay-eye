"""Dependency parsers: detection and extraction over fixture repos.

Separate from ``test_parsers.py`` (interface parsers) since dependency parsers are a distinct
registry/candidate shape (dependency-indexing capability), not registered under
``panopticon.parsers.REGISTRY``.
"""

import unittest
from pathlib import Path

from panopticon.parsers import go_mod

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_GO_REPO = FIXTURES / "sample_go_repo"
SAMPLE_GO_REPO_NO_CONFIG = FIXTURES / "sample_go_repo_no_config"


class TestGoModDetect(unittest.TestCase):
    def test_detects_repo_with_go_mod(self):
        self.assertTrue(go_mod.detect(SAMPLE_GO_REPO))

    def test_does_not_detect_repo_without_go_mod(self):
        with_no_go_mod = FIXTURES / "sample_repo"
        self.assertFalse(go_mod.detect(with_no_go_mod))


class TestGoModExtract(unittest.TestCase):
    def setUp(self):
        self.candidates = go_mod.extract(SAMPLE_GO_REPO)

    def test_self_registers_as_producer_from_module_path_alone(self):
        producer = [c for c in self.candidates if c["role"] == "producer"]
        self.assertEqual(len(producer), 1)
        candidate = producer[0]
        self.assertEqual(candidate["raw_name"], "github.com/acme/svc-b")
        self.assertEqual(candidate["ecosystem"], "go")
        self.assertTrue(candidate["owned"])
        self.assertEqual(candidate["source_file"], "go.mod")

    def test_internal_require_becomes_consumer_candidate_from_go_mod(self):
        go_mod_consumers = [
            c for c in self.candidates
            if c["role"] == "consumer" and c["source_file"] == "go.mod"
        ]
        self.assertEqual(len(go_mod_consumers), 1)
        self.assertEqual(go_mod_consumers[0]["raw_name"], "github.com/acme/shared-lib")
        self.assertIsNone(go_mod_consumers[0]["apis"])

    def test_external_require_produces_no_candidate(self):
        names = {c["raw_name"] for c in self.candidates}
        self.assertNotIn("github.com/pkg/errors", names)

    def test_source_scan_records_imported_subpackages(self):
        go_file_consumers = [
            c for c in self.candidates
            if c["role"] == "consumer" and c["source_file"] == "main.go"
        ]
        self.assertEqual(len(go_file_consumers), 1)
        candidate = go_file_consumers[0]
        self.assertEqual(candidate["raw_name"], "github.com/acme/shared-lib")
        self.assertEqual(
            candidate["apis"],
            ["github.com/acme/shared-lib/client", "github.com/acme/shared-lib/metrics"],
        )

    def test_dependency_of_hint_resolved_on_go_mod_require_line(self):
        go_mod_consumers = [
            c for c in self.candidates
            if c["role"] == "consumer" and c["source_file"] == "go.mod"
        ]
        self.assertEqual(go_mod_consumers[0]["links_to_interface_hint"], "order-processing-api")

    def test_uninitialized_repo_yields_no_candidates(self):
        # No panopticon/config.json → no known org identity → structural detection unavailable.
        self.assertEqual(go_mod.extract(SAMPLE_GO_REPO_NO_CONFIG), [])


if __name__ == "__main__":
    unittest.main()
