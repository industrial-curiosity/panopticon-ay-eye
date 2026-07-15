"""Org-wide diagram rendering from the compiled index: internal-only exclusion, alphabetical
ordering, per-interface (non-deduplicated) edges, navigation links, and (dependency-indexing
capability) combined interface+dependency rendering with kind-based visual distinction and
linked-pair deduplication."""

import unittest

from panopticon.diagrams import relationships_for_repo, render_org_diagram, repo_set
from panopticon.merge import compile_index
from panopticon.dependency_merge import compile_index as compile_dependency_index

from .helpers import load_fixture


def base_shards():
    return {
        "svc-a": load_fixture("local_svc_a.json"),
        "svc-b": load_fixture("local_svc_b.json"),
    }


def base_dependency_shards():
    return {
        "svc-a": load_fixture("local_dep_svc_a.json"),
        "svc-b": load_fixture("local_dep_svc_b.json"),
    }


class TestRepoSet(unittest.TestCase):
    def test_single_repo_entry_is_internal_only(self):
        entry = {
            "owner": {"repo": "svc-a", "component": "x"},
            "producer": [{"repo": "svc-a", "source_files": ["f"]}],
            "consumer": [{"repo": "svc-a", "source_files": ["f"]}],
        }
        self.assertEqual(repo_set(entry), {"svc-a"})

    def test_cross_repo_entry_has_multiple_repos(self):
        entry = {
            "owner": {"repo": "svc-a", "component": "x"},
            "producer": [{"repo": "svc-a", "source_files": ["f"]}],
            "consumer": [{"repo": "svc-b", "source_files": ["f"]}],
        }
        self.assertEqual(repo_set(entry), {"svc-a", "svc-b"})


class TestRelationshipsForRepo(unittest.TestCase):
    def test_cross_repo_interface_appears_in_both_repos_with_correct_direction(self):
        compiled = compile_index(base_shards())
        a_rows = relationships_for_repo(compiled, "svc-a")
        b_rows = relationships_for_repo(compiled, "svc-b")
        order_events_a = next(r for r in a_rows if r["name"] == "order-events")
        order_events_b = next(r for r in b_rows if r["name"] == "order-events")
        self.assertEqual(order_events_a["direction"], "produces")
        self.assertEqual(order_events_a["other_repo"], "svc-b")
        self.assertEqual(order_events_b["direction"], "consumes")
        self.assertEqual(order_events_b["other_repo"], "svc-a")
        self.assertIn("owner", order_events_b["other_role"])

    def test_internal_only_interface_excluded_from_both_repos(self):
        shards = base_shards()
        # svc-a both produces and consumes its own interface, no other repo involved.
        shards["svc-a"]["interfaces"]["internal-only"] = [
            {
                "owner": {"repo": "svc-a", "component": "x"},
                "type": "rest",
                "producer": [{"repo": "svc-a", "source_files": ["f.py"]}],
                "consumer": [{"repo": "svc-a", "source_files": ["f.py"]}],
            }
        ]
        compiled = compile_index(shards)
        rows = relationships_for_repo(compiled, "svc-a")
        self.assertNotIn("internal-only", [r["name"] for r in rows])

    def test_unrelated_repo_has_no_rows(self):
        compiled = compile_index(base_shards())
        self.assertEqual(relationships_for_repo(compiled, "svc-z"), [])

    def test_edges_are_per_interface_not_deduplicated(self):
        compiled = compile_index(base_shards())
        rows = relationships_for_repo(compiled, "svc-a")
        # svc-a has two distinct cross-repo interfaces with svc-b (order-events, orders-api) —
        # both must appear as separate rows, not collapsed into one svc-a/svc-b relationship.
        names = sorted(r["name"] for r in rows if r["other_repo"] == "svc-b")
        self.assertEqual(names, ["order-events", "orders-api"])


class TestRenderOrgDiagram(unittest.TestCase):
    def test_repos_with_external_interfaces_get_alphabetical_sections(self):
        compiled = compile_index(base_shards())
        text = render_org_diagram(compiled)
        self.assertLess(text.index("## svc-a"), text.index("## svc-b"))

    def test_repo_with_only_internal_interfaces_gets_no_section(self):
        shards = {"svc-a": load_fixture("local_svc_a.json")}
        # svc-a's own local index only mentions itself; compiling alone has no cross-repo entries.
        compiled = compile_index(shards)
        text = render_org_diagram(compiled)
        self.assertNotIn("## svc-a", text)
        self.assertIn("setup-guide.md#4-initialize-a-child-repo", text)
        self.assertEqual(text.count('("?")'), 6)

    def test_populated_index_has_no_placeholder_content(self):
        compiled = compile_index(base_shards())
        text = render_org_diagram(compiled)
        self.assertNotIn("setup-guide.md#4-initialize-a-child-repo", text)
        self.assertNotIn('("?")', text)

    def test_diagram_format_tags_the_fenced_block(self):
        compiled = compile_index(base_shards())
        text = render_org_diagram(compiled, diagram_format="mermaid")
        self.assertIn("```mermaid", text)

    def test_default_format_is_mermaid(self):
        compiled = compile_index(base_shards())
        text = render_org_diagram(compiled)
        self.assertIn("```mermaid", text)

    def test_navigation_links_to_child_repo_docs(self):
        # Links live in docs/architecture.md itself, so the href must be relative to docs/ —
        # i.e. "svc-a/architecture.md", not "docs/svc-a/architecture.md" (which would resolve to
        # the non-existent docs/docs/svc-a/architecture.md on GitHub).
        compiled = compile_index(base_shards())
        text = render_org_diagram(compiled)
        self.assertIn("svc-a/architecture.md", text)
        self.assertIn("svc-b/architecture.md", text)
        self.assertNotIn("docs/svc-a/architecture.md", text)
        self.assertNotIn("docs/svc-b/architecture.md", text)

    def test_rendering_is_deterministic(self):
        compiled = compile_index(base_shards())
        self.assertEqual(render_org_diagram(compiled), render_org_diagram(compiled))

    def test_no_click_directive_in_diagram(self):
        # Design D5: navigation is plain markdown links, never diagram-native click directives.
        compiled = compile_index(base_shards())
        text = render_org_diagram(compiled)
        self.assertNotIn("click ", text)


class TestCombinedInterfaceAndDependencyRendering(unittest.TestCase):
    """architecture-diagrams spec (dependency-indexing capability delta): dependency edges
    rendered alongside interface edges, visually distinguished, combined into one section."""

    def test_dependency_only_repo_gets_a_section(self):
        # No interface relationships at all — only a compiled dependency index.
        dep_compiled = compile_dependency_index(base_dependency_shards())
        text = render_org_diagram({}, dep_compiled)
        self.assertIn("## svc-a", text)
        self.assertIn("## svc-b", text)
        self.assertIn("github.com/acme/svc-a", text)

    def test_repo_with_both_gets_one_combined_section_not_two(self):
        iface_compiled = compile_index(base_shards())
        dep_compiled = compile_dependency_index(base_dependency_shards())
        text = render_org_diagram(iface_compiled, dep_compiled)
        self.assertEqual(text.count("## svc-a"), 1)
        self.assertEqual(text.count("## svc-b"), 1)
        # Both an interface name and a dependency name appear under the same svc-a section.
        section = text[text.index("## svc-a"):text.index("## svc-b")]
        self.assertIn("order-events", section)
        self.assertIn("github.com/acme/svc-a", section)

    def test_single_repo_dependency_excluded(self):
        shards = {"svc-a": load_fixture("local_dep_svc_a.json")}
        # svc-a's own local dependency index only mentions itself (self-registration, no
        # consumer) — compiling alone has no cross-repo entries.
        dep_compiled = compile_dependency_index(shards)
        text = render_org_diagram({}, dep_compiled)
        self.assertNotIn("## svc-a", text)

    def test_interface_edge_is_dashed_dependency_edge_is_solid(self):
        iface_compiled = compile_index(base_shards())
        dep_compiled = compile_dependency_index(base_dependency_shards())
        rows = relationships_for_repo(iface_compiled, "svc-a", dep_compiled)
        from panopticon.diagrams import _mermaid_graph

        graph = _mermaid_graph("svc-a", rows)
        self.assertIn("-.->|order-events|", graph)
        self.assertIn("-->|github.com/acme/svc-a|", graph)

    def test_linked_dependency_and_interface_collapse_to_one_edge(self):
        iface_compiled = compile_index(base_shards())
        dep_shards = base_dependency_shards()
        # svc-b's dependency on svc-a's package is explicitly linked to svc-a's "orders-api"
        # interface (both relate svc-a <-> svc-b) via a panopticon-dependency-of hint.
        dep_shards["svc-b"]["dependencies"]["github.com/acme/svc-a"][0]["links_to_interface"] = {
            "name": "orders-api", "type": "rest",
        }
        dep_compiled = compile_dependency_index(dep_shards)
        rows = relationships_for_repo(iface_compiled, "svc-b", dep_compiled)
        orders_api_rows = [r for r in rows if r["other_repo"] == "svc-a" and "orders-api" in r["name"]]
        self.assertEqual(len(orders_api_rows), 1)
        self.assertEqual(orders_api_rows[0]["kind"], "linked")
        self.assertIn("orders-api", orders_api_rows[0]["name"])
        self.assertIn("github.com/acme/svc-a", orders_api_rows[0]["name"])
        text = render_org_diagram(iface_compiled, dep_compiled)
        self.assertIn("==>", text)  # thick/double edge for the linked pair

    def test_unlinked_dependency_and_interface_render_separately(self):
        # Same two repos have both a real interface (order-events, orders-api) and a real
        # dependency relationship, but no panopticon-dependency-of hint links them — no guessing.
        iface_compiled = compile_index(base_shards())
        dep_compiled = compile_dependency_index(base_dependency_shards())
        rows = relationships_for_repo(iface_compiled, "svc-b", dep_compiled)
        kinds = {r["kind"] for r in rows if r["other_repo"] == "svc-a"}
        self.assertEqual(kinds, {"interface", "dependency"})
        self.assertNotIn("linked", kinds)


if __name__ == "__main__":
    unittest.main()
