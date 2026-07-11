"""Doc tooling: deterministic interface rendering, in-place regeneration, layer validation."""

import tempfile
import unittest
from pathlib import Path

from panopticon.docs import (
    diagram_section_problems,
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
    (root / "architecture.md").write_text(
        "# svc-a — architecture overview\n\n## Architecture diagram\n\n```mermaid\ngraph TD\n  api --> worker\n```\n"
    )
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


class TestDiagramSection(unittest.TestCase):
    def write_architecture(self, tmp, text):
        (Path(tmp) / "architecture.md").write_text(text)

    def test_well_formed_mermaid_section_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_architecture(tmp, "# x\n\n## Architecture diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n")
            self.assertEqual(diagram_section_problems(tmp), [])

    def test_default_format_is_mermaid(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_architecture(tmp, "# x\n\n## Architecture diagram\n\n```plantuml\n@startuml\n@enduml\n```\n")
            problems = diagram_section_problems(tmp)
        self.assertEqual(len(problems), 1)
        self.assertIn("expected 'mermaid'", problems[0])

    def test_configured_format_is_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_architecture(tmp, "# x\n\n## Architecture diagram\n\n```plantuml\n@startuml\n@enduml\n```\n")
            self.assertEqual(diagram_section_problems(tmp, diagram_format="plantuml"), [])

    def test_missing_heading_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_architecture(tmp, "# x\n\nno diagram section here\n")
            problems = diagram_section_problems(tmp)
        self.assertEqual(len(problems), 1)
        self.assertIn("missing", problems[0])
        self.assertIn("Architecture diagram", problems[0])

    def test_missing_fenced_block_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_architecture(tmp, "# x\n\n## Architecture diagram\n\njust prose, no fence\n")
            problems = diagram_section_problems(tmp)
        self.assertEqual(len(problems), 1)
        self.assertIn("no fenced code block directly under", problems[0])

    def test_fence_not_directly_under_heading_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_architecture(
                tmp,
                "# x\n\n## Architecture diagram\n\nSome intro prose first.\n\n```mermaid\ngraph TD\nA-->B\n```\n",
            )
            problems = diagram_section_problems(tmp)
        self.assertEqual(len(problems), 1)
        self.assertIn("no fenced code block directly under", problems[0])

    def test_wrong_language_fenced_block_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_architecture(tmp, "# x\n\n## Architecture diagram\n\n```plantuml\n@startuml\n@enduml\n```\n")
            problems = diagram_section_problems(tmp, diagram_format="mermaid")
        self.assertEqual(len(problems), 1)
        self.assertIn("tagged 'plantuml'", problems[0])
        self.assertIn("expected 'mermaid'", problems[0])

    def test_validate_docs_includes_diagram_problems(self):
        doc = load_fixture("local_svc_a.json")
        with tempfile.TemporaryDirectory() as tmp:
            make_docs_tree(tmp)
            (Path(tmp) / "architecture.md").write_text("# svc-a — architecture overview\n\nno diagram here\n")
            write_interface_docs(doc, tmp, "svc-a")
            problems = validate_docs(tmp)
        self.assertEqual(len(problems), 1)
        self.assertIn("architecture diagram section missing", problems[0])

    def test_validate_docs_skips_diagram_check_when_architecture_doc_itself_missing(self):
        # Missing-file case is already reported once as "architecture overview layer missing" —
        # no double-reporting a diagram-section problem for a file that doesn't exist.
        with tempfile.TemporaryDirectory() as tmp:
            problems = validate_docs(tmp)
        architecture_problems = [p for p in problems if "architecture" in p]
        self.assertEqual(len(architecture_problems), 1)


if __name__ == "__main__":
    unittest.main()
