"""Index schema: load/validate/save round-trips and validation failures."""

import tempfile
import unittest
from pathlib import Path

from panopticon.index import (
    KIND_COMPILED,
    KIND_LOCAL,
    IndexValidationError,
    dumps_index,
    empty_index,
    load_index,
    save_index,
    validate_index,
)

from .helpers import load_fixture


class TestValidation(unittest.TestCase):
    def test_valid_local_fixture(self):
        doc = load_fixture("local_svc_a.json")
        validate_index(doc, kind=KIND_LOCAL, repo="svc-a")

    def test_missing_schema_version(self):
        doc = load_fixture("local_svc_a.json")
        del doc["schema_version"]
        with self.assertRaises(IndexValidationError) as ctx:
            validate_index(doc)
        self.assertIn("schema_version", str(ctx.exception))

    def test_local_index_must_not_carry_conflicts(self):
        doc = load_fixture("local_svc_a.json")
        doc["conflicts"] = []
        with self.assertRaises(IndexValidationError) as ctx:
            validate_index(doc, kind=KIND_LOCAL)
        self.assertIn("conflicts", str(ctx.exception))

    def test_local_index_mentions_only_itself(self):
        doc = load_fixture("local_svc_a.json")
        with self.assertRaises(IndexValidationError) as ctx:
            validate_index(doc, kind=KIND_LOCAL, repo="svc-b")
        self.assertIn("may only mention itself", str(ctx.exception))

    def test_empty_entry_rejected(self):
        doc = empty_index()
        doc["interfaces"]["ghost"] = [
            {"owner": None, "type": "rest", "consumer": [], "producer": []}
        ]
        with self.assertRaises(IndexValidationError) as ctx:
            validate_index(doc)
        self.assertIn("empty entries must be removed", str(ctx.exception))

    def test_empty_key_rejected(self):
        doc = empty_index()
        doc["interfaces"]["ghost"] = []
        with self.assertRaises(IndexValidationError):
            validate_index(doc)

    def test_compiled_requires_conflicts_list(self):
        doc = empty_index()
        with self.assertRaises(IndexValidationError) as ctx:
            validate_index(doc, kind=KIND_COMPILED)
        self.assertIn("conflicts", str(ctx.exception))

    def test_duplicate_type_under_key_rejected(self):
        doc = load_fixture("local_svc_a.json")
        doc["interfaces"]["orders-api"].append(doc["interfaces"]["orders-api"][0])
        with self.assertRaises(IndexValidationError) as ctx:
            validate_index(doc, repo="svc-a")
        self.assertIn("duplicate interface object", str(ctx.exception))

    def test_extracted_by_only_llm(self):
        doc = load_fixture("local_svc_a.json")
        doc["interfaces"]["orders-api"][0]["extracted_by"] = "human"
        with self.assertRaises(IndexValidationError):
            validate_index(doc, repo="svc-a")


class TestRoundTrip(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        doc = load_fixture("local_svc_a.json")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon" / "index.json"
            save_index(doc, path, kind=KIND_LOCAL, repo="svc-a")
            loaded = load_index(path, kind=KIND_LOCAL, repo="svc-a")
        self.assertEqual(doc, loaded)

    def test_dumps_is_deterministic_regardless_of_input_order(self):
        doc = load_fixture("local_svc_a.json")
        reordered = {
            "interfaces": dict(reversed(list(doc["interfaces"].items()))),
            "schema_version": doc["schema_version"],
        }
        self.assertEqual(dumps_index(doc), dumps_index(reordered))

    def test_load_missing_file_reports_path(self):
        with self.assertRaises(IndexValidationError) as ctx:
            load_index("/nonexistent/index.json")
        self.assertIn("/nonexistent/index.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
