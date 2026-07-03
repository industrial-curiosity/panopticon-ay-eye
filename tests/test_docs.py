"""Doc tooling: deterministic interface rendering, in-place regeneration, layer validation."""

import tempfile
import unittest
from pathlib import Path

from panopticon.docs import (
    prune_component_docs,
    regenerate,
    render_interface_docs,
    validate_docs,
    write_interface_docs,
)

from .helpers import load_fixture


def make_docs_tree(root):
    root = Path(root)
    (root / "components").mkdir(parents=True)
    (root / "architecture.md").write_text("# svc-a — architecture overview\n")
    (root / "operations.md").write_text("# svc-a — operations\n")
    (root / "components" / "api.md").write_text("# api\n")
    (root / "components" / "worker.md").write_text("# worker\n")


class TestRendering(unittest.TestCase):
    def test_rendering_is_deterministic_and_reflects_index(self):
        doc = load_fixture("local_svc_a.json")
        first = render_interface_docs(doc, "svc-a")
        second = render_interface_docs(doc, "svc-a")
        self.assertEqual(first, second)
        self.assertIn("## `order-events` (kafka)", first)
        self.assertIn("## `orders-api` (rest)", first)
        self.assertIn("svc-a / order-service (this repo)", first)
        self.assertIn("`config/kafka-topics.json`", first)

    def test_rendered_docs_track_index_changes(self):
        doc = load_fixture("local_svc_a.json")
        with tempfile.TemporaryDirectory() as tmp:
            write_interface_docs(doc, tmp, "svc-a")
            del doc["interfaces"]["orders-api"]
            path = write_interface_docs(doc, tmp, "svc-a")
            text = path.read_text()
        self.assertNotIn("orders-api", text)
        self.assertIn("order-events", text)

    def test_empty_index_renders_explicit_statement(self):
        from panopticon.index import empty_index

        text = render_interface_docs(empty_index(), "svc-a")
        self.assertIn("declares no interfaces", text)

    def test_llm_provenance_is_visible(self):
        doc = load_fixture("local_svc_a.json")
        doc["interfaces"]["order-events"][0]["extracted_by"] = "llm"
        self.assertIn("extracted by LLM", render_interface_docs(doc, "svc-a"))


class TestRegeneration(unittest.TestCase):
    def test_regenerate_updates_in_place_and_prunes_deleted_components(self):
        doc = load_fixture("local_svc_a.json")
        with tempfile.TemporaryDirectory() as tmp:
            make_docs_tree(tmp)
            result = regenerate(tmp, doc, "svc-a", current_components=["api"])
            self.assertEqual(result["removed_components"], ["worker"])
            self.assertFalse((Path(tmp) / "components" / "worker.md").exists())
            self.assertTrue((Path(tmp) / "components" / "api.md").exists())
            # a second run is a no-op, not a duplicate
            again = regenerate(tmp, doc, "svc-a", current_components=["api"])
            self.assertEqual(again["removed_components"], [])
            self.assertEqual(sorted(p.name for p in Path(tmp).glob("*.md")),
                             ["architecture.md", "interfaces.md", "operations.md"])

    def test_prune_without_components_dir_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(prune_component_docs(tmp, ["api"]), [])


class TestValidation(unittest.TestCase):
    def test_complete_tree_is_valid(self):
        doc = load_fixture("local_svc_a.json")
        with tempfile.TemporaryDirectory() as tmp:
            make_docs_tree(tmp)
            write_interface_docs(doc, tmp, "svc-a")
            self.assertEqual(validate_docs(tmp), [])

    def test_missing_layers_are_each_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            problems = validate_docs(tmp)
        text = "\n".join(problems)
        self.assertEqual(len(problems), 4)
        for fragment in ("architecture overview", "interface docs", "operational docs", "per-component docs"):
            self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
