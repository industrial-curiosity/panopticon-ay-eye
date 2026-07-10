"""Combined-report TL;DR: de-duplication, rendering, and assembly (pr-evaluation spec: "Combined
report leads with a de-duplicated action list")."""

import json
import tempfile
import unittest
from pathlib import Path

from panopticon.report import (
    PASS_MESSAGE,
    build_combined_report,
    dedupe_actions,
    load_actions,
    render_tldr,
)


class TestDedupeActions(unittest.TestCase):
    def test_collapses_same_kind_and_target(self):
        actions = [{"kind": "update_index"}, {"kind": "update_index"}]
        self.assertEqual(dedupe_actions(actions), [{"kind": "update_index"}])

    def test_keeps_distinct_targets(self):
        actions = [
            {"kind": "regenerate_doc", "target": "docs/architecture.md"},
            {"kind": "regenerate_doc", "target": "docs/operations.md"},
        ]
        deduped = dedupe_actions(actions)
        self.assertEqual(len(deduped), 2)
        targets = {a["target"] for a in deduped}
        self.assertEqual(targets, {"docs/architecture.md", "docs/operations.md"})

    def test_orders_by_fixed_section_order_regardless_of_input_order(self):
        actions = [
            {"kind": "commit_and_push"},
            {"kind": "resolve_conflict", "target": "orders-api"},
            {"kind": "update_index"},
            {"kind": "regenerate_doc", "target": "docs/architecture.md"},
        ]
        kinds = [a["kind"] for a in dedupe_actions(actions)]
        self.assertEqual(kinds, ["update_index", "regenerate_doc", "resolve_conflict", "commit_and_push"])


class TestRenderTldr(unittest.TestCase):
    def test_empty_actions_says_all_passed(self):
        self.assertEqual(render_tldr([]), PASS_MESSAGE)

    def test_lists_deduped_actions_with_targets_interpolated(self):
        tldr = render_tldr(
            [
                {"kind": "update_index"},
                {"kind": "regenerate_doc", "target": "docs/architecture.md"},
                {"kind": "commit_and_push"},
            ]
        )
        self.assertIn("panopticon/index.json", tldr)
        self.assertIn("docs/architecture.md", tldr)
        self.assertIn("this same PR's branch", tldr)

    def test_same_fix_from_two_checks_appears_once(self):
        # drift's interfaces.md finding and currency's stale-index finding both emit update_index
        tldr = render_tldr([{"kind": "update_index"}, {"kind": "update_index"}, {"kind": "commit_and_push"}])
        bullet_count = sum(1 for line in tldr.splitlines() if line.startswith("- Update `panopticon/index.json`"))
        self.assertEqual(bullet_count, 1)


class TestBuildCombinedReport(unittest.TestCase):
    def test_tldr_appears_at_both_ends_with_detail_between(self):
        sections = ["## drift detail", "## currency detail"]
        actions = [{"kind": "update_index"}]
        report = build_combined_report(sections, actions)
        self.assertEqual(report.count("TL;DR"), 2)
        self.assertLess(report.index("TL;DR"), report.index("## drift detail"))
        self.assertLess(report.index("## currency detail"), report.rindex("TL;DR"))

    def test_all_passed_tldr_at_both_ends(self):
        report = build_combined_report(["## all good"], [])
        self.assertEqual(report.count(PASS_MESSAGE), 2)


class TestLoadActions(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_actions(Path(tmp) / "nope.json"), [])

    def test_reads_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            path.write_text(json.dumps([{"kind": "commit_and_push"}]), encoding="utf-8")
            self.assertEqual(load_actions(path), [{"kind": "commit_and_push"}])


if __name__ == "__main__":
    unittest.main()
