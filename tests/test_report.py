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
        actions = [{"kind": "run_doc_generation"}, {"kind": "run_doc_generation"}]
        self.assertEqual(dedupe_actions(actions), [{"kind": "run_doc_generation"}])

    def test_many_stale_docs_and_index_still_collapse_to_one(self):
        # Drift alone can report many stale docs plus interfaces.md; all of it is one action.
        actions = [{"kind": "run_doc_generation"}] * 6
        self.assertEqual(dedupe_actions(actions), [{"kind": "run_doc_generation"}])

    def test_keeps_distinct_conflict_targets(self):
        actions = [
            {"kind": "resolve_conflict", "target": "orders-api"},
            {"kind": "resolve_conflict", "target": "order-events"},
        ]
        deduped = dedupe_actions(actions)
        self.assertEqual(len(deduped), 2)
        targets = {a["target"] for a in deduped}
        self.assertEqual(targets, {"orders-api", "order-events"})

    def test_orders_by_fixed_section_order_regardless_of_input_order(self):
        actions = [
            {"kind": "commit_and_push"},
            {"kind": "resolve_conflict", "target": "orders-api"},
            {"kind": "run_doc_generation"},
        ]
        kinds = [a["kind"] for a in dedupe_actions(actions)]
        self.assertEqual(kinds, ["run_doc_generation", "resolve_conflict", "commit_and_push"])


class TestRenderTldr(unittest.TestCase):
    def test_empty_actions_says_all_passed(self):
        self.assertEqual(render_tldr([]), PASS_MESSAGE)

    def test_lists_deduped_actions(self):
        tldr = render_tldr([{"kind": "run_doc_generation"}, {"kind": "commit_and_push"}])
        self.assertIn("panopticon-doc-generation skill", tldr)
        self.assertIn("this same PR's branch", tldr)

    def test_many_stale_docs_and_index_yield_one_tldr_line(self):
        # Mirrors the real report that motivated this: 5 stale docs + a stale index from two
        # different checks, all collapsing to a single "run it once" instruction.
        actions = [{"kind": "run_doc_generation"}] * 6 + [{"kind": "commit_and_push"}]
        tldr = render_tldr(actions)
        bullet_lines = [line for line in tldr.splitlines() if line.startswith("- ")]
        self.assertEqual(len(bullet_lines), 2)  # run_doc_generation once, commit_and_push once

    def test_conflict_stays_separate_from_doc_generation(self):
        tldr = render_tldr(
            [
                {"kind": "run_doc_generation"},
                {"kind": "resolve_conflict", "target": "orders-api"},
                {"kind": "commit_and_push"},
            ]
        )
        bullet_lines = [line for line in tldr.splitlines() if line.startswith("- ")]
        self.assertEqual(len(bullet_lines), 3)
        self.assertIn("orders-api", tldr)


class TestBuildCombinedReport(unittest.TestCase):
    def test_tldr_appears_at_both_ends_with_detail_between(self):
        sections = ["## drift detail", "## currency detail"]
        actions = [{"kind": "run_doc_generation"}]
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
