"""Dependency index schema: load/validate/save round-trips and validation failures."""

import tempfile
import unittest
from pathlib import Path

from panopticon.dependencies import (
    CONFLICT_REASON_OWNERSHIP_DISPUTE,
    CONFLICT_REASON_UNREGISTERED_PRODUCER,
    KIND_COMPILED,
    KIND_LOCAL,
    DependencyIndexValidationError,
    dumps_index,
    empty_index,
    load_index,
    save_index,
    validate_index,
)

from .helpers import load_fixture


class TestValidation(unittest.TestCase):
    def test_valid_local_fixture(self):
        doc = load_fixture("local_dep_svc_a.json")
        validate_index(doc, kind=KIND_LOCAL, repo="svc-a")

    def test_valid_consumer_fixture_with_apis(self):
        doc = load_fixture("local_dep_svc_b.json")
        validate_index(doc, kind=KIND_LOCAL, repo="svc-b")

    def test_missing_schema_version(self):
        doc = load_fixture("local_dep_svc_a.json")
        del doc["schema_version"]
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc)
        self.assertIn("schema_version", str(ctx.exception))

    def test_local_index_must_not_carry_conflicts(self):
        doc = load_fixture("local_dep_svc_a.json")
        doc["conflicts"] = []
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, kind=KIND_LOCAL)
        self.assertIn("conflicts", str(ctx.exception))

    def test_local_index_mentions_only_itself(self):
        doc = load_fixture("local_dep_svc_a.json")
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, kind=KIND_LOCAL, repo="svc-b")
        self.assertIn("may only mention itself", str(ctx.exception))

    def test_empty_entry_rejected(self):
        doc = empty_index()
        doc["dependencies"]["ghost"] = [
            {"owner": None, "ecosystem": "go", "consumer": [], "producer": []}
        ]
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc)
        self.assertIn("empty entries must be removed", str(ctx.exception))

    def test_empty_key_rejected(self):
        doc = empty_index()
        doc["dependencies"]["ghost"] = []
        with self.assertRaises(DependencyIndexValidationError):
            validate_index(doc)

    def test_compiled_requires_conflicts_list(self):
        doc = empty_index()
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, kind=KIND_COMPILED)
        self.assertIn("conflicts", str(ctx.exception))

    def test_duplicate_ecosystem_under_key_rejected(self):
        doc = load_fixture("local_dep_svc_a.json")
        doc["dependencies"]["github.com/acme/svc-a"].append(
            doc["dependencies"]["github.com/acme/svc-a"][0]
        )
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, repo="svc-a")
        self.assertIn("duplicate dependency object", str(ctx.exception))

    def test_extracted_by_only_llm(self):
        doc = load_fixture("local_dep_svc_a.json")
        doc["dependencies"]["github.com/acme/svc-a"][0]["extracted_by"] = "human"
        with self.assertRaises(DependencyIndexValidationError):
            validate_index(doc, repo="svc-a")

    def test_apis_rejected_on_producer_object(self):
        doc = load_fixture("local_dep_svc_a.json")
        doc["dependencies"]["github.com/acme/svc-a"][0]["producer"][0]["apis"] = ["x"]
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, repo="svc-a")
        self.assertIn("unknown repo-object fields", str(ctx.exception))

    def test_apis_must_be_list_of_strings(self):
        doc = load_fixture("local_dep_svc_b.json")
        doc["dependencies"]["github.com/acme/svc-a"][0]["consumer"][0]["apis"] = "not-a-list"
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, repo="svc-b")
        self.assertIn("'apis' must be a list", str(ctx.exception))

    def test_links_to_interface_requires_name_and_type(self):
        doc = load_fixture("local_dep_svc_a.json")
        doc["dependencies"]["github.com/acme/svc-a"][0]["links_to_interface"] = {"name": "orders-api"}
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, repo="svc-a")
        self.assertIn("links_to_interface", str(ctx.exception))

    def test_links_to_interface_valid(self):
        doc = load_fixture("local_dep_svc_a.json")
        doc["dependencies"]["github.com/acme/svc-a"][0]["links_to_interface"] = {
            "name": "orders-api",
            "type": "rest",
        }
        validate_index(doc, kind=KIND_LOCAL, repo="svc-a")

    def test_conflict_reason_must_be_known(self):
        doc = empty_index(KIND_COMPILED)
        doc["conflicts"] = [
            {
                "name": "x",
                "ecosystem": "go",
                "reason": "not-a-real-reason",
                "details": "d",
                "claims": [],
            }
        ]
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, kind=KIND_COMPILED)
        self.assertIn("reason", str(ctx.exception))

    def test_unregistered_producer_conflict_allows_empty_claims(self):
        doc = empty_index(KIND_COMPILED)
        doc["conflicts"] = [
            {
                "name": "x",
                "ecosystem": "go",
                "reason": CONFLICT_REASON_UNREGISTERED_PRODUCER,
                "details": "consumer svc-b references x with no known producer",
                "claims": [],
            }
        ]
        validate_index(doc, kind=KIND_COMPILED)

    def test_ownership_dispute_requires_nonempty_claims(self):
        doc = empty_index(KIND_COMPILED)
        doc["conflicts"] = [
            {
                "name": "x",
                "ecosystem": "go",
                "reason": CONFLICT_REASON_OWNERSHIP_DISPUTE,
                "details": "d",
                "claims": [],
            }
        ]
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            validate_index(doc, kind=KIND_COMPILED)
        self.assertIn("non-empty", str(ctx.exception))


class TestRoundTrip(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        doc = load_fixture("local_dep_svc_b.json")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon" / "dependencies.json"
            save_index(doc, path, kind=KIND_LOCAL, repo="svc-b")
            loaded = load_index(path, kind=KIND_LOCAL, repo="svc-b")
        self.assertEqual(doc, loaded)

    def test_dumps_is_deterministic_regardless_of_input_order(self):
        doc = load_fixture("local_dep_svc_a.json")
        reordered = {
            "dependencies": dict(reversed(list(doc["dependencies"].items()))),
            "schema_version": doc["schema_version"],
        }
        self.assertEqual(dumps_index(doc), dumps_index(reordered))

    def test_dumps_dedupes_and_sorts_apis(self):
        doc = load_fixture("local_dep_svc_b.json")
        consumer = doc["dependencies"]["github.com/acme/svc-a"][0]["consumer"][0]
        consumer["apis"] = ["b/pkg", "a/pkg", "a/pkg"]
        dumped = dumps_index(doc)
        self.assertIn('"a/pkg"', dumped)
        self.assertLess(dumped.index('"a/pkg"'), dumped.index('"b/pkg"'))
        self.assertEqual(dumped.count('"a/pkg"'), 1)

    def test_load_missing_file_reports_path(self):
        with self.assertRaises(DependencyIndexValidationError) as ctx:
            load_index("/nonexistent/dependencies.json")
        self.assertIn("/nonexistent/dependencies.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
