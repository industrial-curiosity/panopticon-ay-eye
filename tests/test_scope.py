"""Deterministic analysis-scope policy tests."""

import tempfile
import unittest
from pathlib import Path

from panopticon.scope import (
    ILLUSTRATIVE_DIRECTORIES,
    declaration_reason,
    excluded_directories,
    file_reason,
    path_reason,
    redact_ignored_declarations,
)


class TestPathScope(unittest.TestCase):
    def test_every_illustrative_directory_is_excluded_case_insensitively(self):
        for directory in ILLUSTRATIVE_DIRECTORIES:
            with self.subTest(directory=directory):
                self.assertEqual(path_reason(f"src/{directory.upper()}/config.yml"),
                                 f"illustrative directory: {directory.upper()}")

    def test_similar_production_path_is_not_excluded(self):
        self.assertIsNone(path_reason("src/sample-service/config.yml"))

    def test_header_file_hint_is_required_within_first_five_nonblank_lines(self):
        self.assertEqual(file_reason("config.yml", "# panopticon-ignore file\nkey: value\n"),
                         "explicit file hint")
        text = "\n".join(["# note"] * 6 + ["# panopticon-ignore file"])
        self.assertIsNone(file_reason("config.yml", text))

    def test_declaration_hint_applies_only_to_same_or_previous_line(self):
        text = "# panopticon-ignore declaration\ntopic: ignored\ntopic: kept\n"
        self.assertEqual(declaration_reason(text, 2), "explicit declaration hint")
        self.assertIsNone(declaration_reason(text, 3))

    def test_redaction_removes_annotation_and_annotated_declaration(self):
        text = "# panopticon-ignore declaration\ntopic: ignored\ntopic: kept\n"
        self.assertEqual(redact_ignored_declarations(text), "topic: kept\n")

    def test_excluded_directories_are_repository_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "examples" / "nested").mkdir(parents=True)
            (root / "src" / "sample-service").mkdir(parents=True)
            self.assertEqual(excluded_directories(root), ("examples",))


if __name__ == "__main__":
    unittest.main()
