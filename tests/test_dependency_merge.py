"""Dependency merge core: compile reproducibility, conflict cases (ownership-dispute and the
dependency-specific unregistered-producer), simulation parity with the real merge — mirroring
test_merge.py's coverage for the dependency schema."""

import copy
import tempfile
import unittest
from pathlib import Path

from panopticon.config import ConfigError
from panopticon.dependencies import KIND_COMPILED, dumps_index, empty_index, validate_index
from panopticon.dependency_merge import (
    collect_actions,
    compile_index,
    diff_compiled,
    merge_into_instance,
    replace_shard,
    shards_from_compiled,
    simulate_merge,
)

from .helpers import load_fixture


def base_shards():
    return {
        "svc-a": load_fixture("local_dep_svc_a.json"),
        "svc-b": load_fixture("local_dep_svc_b.json"),
    }


class TestCompile(unittest.TestCase):
    def test_union_of_consumers_and_producers(self):
        compiled = compile_index(base_shards())
        validate_index(compiled, kind=KIND_COMPILED)
        entry = compiled["dependencies"]["github.com/acme/svc-a"][0]
        self.assertEqual(entry["owner"], {"repo": "svc-a", "component": None})
        self.assertEqual([r["repo"] for r in entry["producer"]], ["svc-a"])
        self.assertEqual([r["repo"] for r in entry["consumer"]], ["svc-b"])
        self.assertEqual(entry["consumer"][0]["apis"], ["github.com/acme/svc-a/client"])
        self.assertEqual(compiled["conflicts"], [])

    def test_compile_is_byte_identical(self):
        first = dumps_index(compile_index(base_shards()))
        second = dumps_index(compile_index(copy.deepcopy(base_shards())))
        self.assertEqual(first, second)

    def test_shards_from_compiled_round_trips(self):
        compiled = compile_index(base_shards())
        recompiled = compile_index(shards_from_compiled(compiled))
        self.assertEqual(dumps_index(compiled), dumps_index(recompiled))

    def test_round_trip_preserves_conflicts(self):
        shards = base_shards()
        shards["svc-c"] = load_fixture("local_dep_svc_c_conflict.json")
        compiled = compile_index(shards)
        self.assertEqual(len(compiled["conflicts"]), 1)
        recompiled = compile_index(shards_from_compiled(compiled))
        self.assertEqual(dumps_index(compiled), dumps_index(recompiled))


class TestConflicts(unittest.TestCase):
    def test_ownership_dispute(self):
        shards = base_shards()
        shards["svc-c"] = load_fixture("local_dep_svc_c_conflict.json")
        compiled = compile_index(shards)
        (conflict,) = compiled["conflicts"]
        self.assertEqual(conflict["reason"], "ownership-dispute")
        self.assertEqual(conflict["name"], "github.com/acme/svc-a")
        self.assertEqual([c["claimed_by"] for c in conflict["claims"]], ["svc-a", "svc-c"])
        # disputed ownership resolves to null until the dispute clears
        self.assertIsNone(compiled["dependencies"]["github.com/acme/svc-a"][0]["owner"])

    def test_unregistered_producer(self):
        # svc-b alone: a consumer with no producer shard present anywhere.
        compiled = compile_index({"svc-b": load_fixture("local_dep_svc_b.json")})
        (conflict,) = compiled["conflicts"]
        self.assertEqual(conflict["reason"], "unregistered-producer")
        self.assertEqual(conflict["name"], "github.com/acme/svc-a")
        self.assertEqual(conflict["claims"], [])
        self.assertIsNone(compiled["dependencies"]["github.com/acme/svc-a"][0]["owner"])

    def test_producer_present_resolves_unregistered_producer(self):
        # Once svc-a's producer shard is present too, the conflict clears.
        compiled = compile_index(base_shards())
        self.assertEqual(compiled["conflicts"], [])

    def test_no_owner_attribution_mismatch_category(self):
        # A dependency has no attribution-mismatch category (module docstring) — a non-self owner
        # claim in a shard is simply ignored, never turned into a conflict.
        shards = base_shards()
        shards["svc-b"]["dependencies"]["github.com/acme/svc-a"][0]["owner"] = {
            "repo": "svc-z",
            "component": "legacy",
        }
        compiled = compile_index(shards)
        self.assertEqual(compiled["conflicts"], [])
        self.assertEqual(
            compiled["dependencies"]["github.com/acme/svc-a"][0]["owner"], {"repo": "svc-a", "component": None}
        )

    def test_shard_replace_clears_stale_conflicts(self):
        shards = base_shards()
        shards["svc-c"] = load_fixture("local_dep_svc_c_conflict.json")
        self.assertEqual(len(compile_index(shards)["conflicts"]), 1)
        withdrawn = load_fixture("local_dep_svc_c_conflict.json")
        del withdrawn["dependencies"]["github.com/acme/svc-a"]
        shards = replace_shard(shards, "svc-c", withdrawn)
        self.assertEqual(compile_index(shards)["conflicts"], [])


class TestEntryLifecycle(unittest.TestCase):
    def test_last_repo_removal_drops_object_and_key(self):
        shards = base_shards()
        local_a = load_fixture("local_dep_svc_a.json")
        del local_a["dependencies"]["github.com/acme/svc-a"]
        local_b = load_fixture("local_dep_svc_b.json")
        del local_b["dependencies"]["github.com/acme/svc-a"]
        shards = replace_shard(replace_shard(shards, "svc-a", local_a), "svc-b", local_b)
        compiled = compile_index(shards)
        self.assertNotIn("github.com/acme/svc-a", compiled["dependencies"])


class TestSimulationParity(unittest.TestCase):
    def write_instance(self, tmp, shards):
        instance = Path(tmp)
        compiled = compile_index(shards)
        (instance / "dependencies").mkdir()
        for repo, shard in shards.items():
            (instance / "dependencies" / f"{repo}.json").write_text(dumps_index(shard))
        (instance / "dependencies" / "index.json").write_text(dumps_index(compiled))
        return instance, compiled

    def test_simulation_matches_real_merge(self):
        incoming = load_fixture("local_dep_svc_c_conflict.json")
        with tempfile.TemporaryDirectory() as tmp:
            instance, compiled = self.write_instance(tmp, base_shards())
            simulated = simulate_merge(incoming, compiled, "svc-c")
            merged = merge_into_instance(instance, "svc-c", incoming)
        self.assertEqual(simulated, merged)
        self.assertEqual(len(simulated["conflicts"]["new"]), 1)
        self.assertEqual(simulated["conflicts"]["new"][0]["reason"], "ownership-dispute")

    def test_clean_simulation_reports_no_conflicts(self):
        compiled = compile_index(base_shards())
        report = simulate_merge(load_fixture("local_dep_svc_b.json"), compiled, "svc-b")
        self.assertEqual(report["conflicts"], {"new": [], "resolved": [], "unchanged": []})
        self.assertEqual(report["added"], [])
        self.assertEqual(report["removed"], [])

    def test_merge_writes_reproducible_compiled_index(self):
        incoming = load_fixture("local_dep_svc_c_conflict.json")
        outputs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                instance, _ = self.write_instance(tmp, base_shards())
                merge_into_instance(instance, "svc-c", incoming)
                outputs.append((instance / "dependencies" / "index.json").read_text())
        self.assertEqual(outputs[0], outputs[1])

    def test_empty_local_index_removes_shard(self):
        with tempfile.TemporaryDirectory() as tmp:
            instance, _ = self.write_instance(tmp, base_shards())
            report = merge_into_instance(instance, "svc-b", empty_index())
            self.assertFalse((instance / "dependencies" / "svc-b.json").exists())
        self.assertTrue(report["removed"] or report["changed"])

    def test_merge_writes_the_org_diagram_with_dependency_edges(self):
        # As of group 8 (architecture-diagrams delta): the dependency merge path shares
        # diagrams.write_org_diagram with the interface merge path, so it also rebuilds the org
        # diagram — with dependency edges rendered (solid, per the module's kind-based styling).
        with tempfile.TemporaryDirectory() as tmp:
            instance, _ = self.write_instance(tmp, {"svc-a": load_fixture("local_dep_svc_a.json")})
            merge_into_instance(instance, "svc-b", load_fixture("local_dep_svc_b.json"))
            text = (instance / "docs" / "architecture.md").read_text()
        self.assertIn("## svc-a", text)
        self.assertIn("## svc-b", text)
        self.assertIn("-->", text)

    def test_merge_picks_up_the_current_interface_index_too(self):
        # write_org_diagram reads both compiled indices fresh from disk, so a dependency-only
        # merge still renders whatever interface relationships the instance already has, rather
        # than rendering from a stale/absent interface index.
        from panopticon.dependencies import dumps_index as dumps_dep_index

        with tempfile.TemporaryDirectory() as tmp:
            instance = Path(tmp)
            (instance / "interfaces").mkdir()
            iface_shards = {"svc-a": load_fixture("local_svc_a.json"), "svc-b": load_fixture("local_svc_b.json")}
            from panopticon.merge import compile_index as compile_iface_index
            from panopticon.index import dumps_index as dumps_iface_index

            iface_compiled = compile_iface_index(iface_shards)
            for repo, shard in iface_shards.items():
                (instance / "interfaces" / f"{repo}.json").write_text(dumps_iface_index(shard))
            (instance / "interfaces" / "index.json").write_text(dumps_iface_index(iface_compiled))
            (instance / "dependencies").mkdir()
            dep_compiled = compile_index({"svc-a": load_fixture("local_dep_svc_a.json")})
            (instance / "dependencies" / "index.json").write_text(dumps_dep_index(dep_compiled))

            merge_into_instance(instance, "svc-b", load_fixture("local_dep_svc_b.json"))
            text = (instance / "docs" / "architecture.md").read_text()
        # svc-a/svc-b's interface relationship (order-events, orders-api) still renders.
        self.assertIn("order-events", text)


class TestDiff(unittest.TestCase):
    def test_diff_identity(self):
        compiled = compile_index(base_shards())
        report = diff_compiled(compiled, compiled, "svc-a")
        self.assertEqual(report["added"], [])
        self.assertEqual(report["removed"], [])
        self.assertEqual(report["changed"], [])


class TestCollectActions(unittest.TestCase):
    def test_no_new_conflicts_has_no_actions(self):
        report = diff_compiled(compile_index(base_shards()), compile_index(base_shards()), "svc-a")
        self.assertEqual(collect_actions(report), [])

    def test_new_conflict_yields_resolve_conflict_and_commit_push(self):
        compiled = compile_index(base_shards())
        conflicting = replace_shard(base_shards(), "svc-c", load_fixture("local_dep_svc_c_conflict.json"))
        after = compile_index(conflicting)
        report = diff_compiled(compiled, after, "svc-c")
        actions = collect_actions(report)
        self.assertIn({"kind": "resolve_conflict", "target": "github.com/acme/svc-a"}, actions)
        self.assertIn({"kind": "commit_and_push"}, actions)


class TestCli(unittest.TestCase):
    """The `python3 -m panopticon.dependency_merge` CLI."""

    def setUp(self):
        import tempfile as _tempfile

        self._tmp = _tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.instance = self.tmp / "instance"
        shards = base_shards()
        (self.instance / "dependencies").mkdir(parents=True)
        for repo, shard in shards.items():
            (self.instance / "dependencies" / f"{repo}.json").write_text(dumps_index(shard))
        compiled = compile_index(shards)
        (self.instance / "dependencies" / "index.json").write_text(dumps_index(compiled))
        self.conflicting_local = self.tmp / "local_c.json"
        self.conflicting_local.write_text(dumps_index(load_fixture("local_dep_svc_c_conflict.json")))

    def run_cli(self, *argv):
        import contextlib
        import io

        from panopticon.dependency_merge import main

        with contextlib.redirect_stdout(io.StringIO()):
            return main(list(argv))

    def test_simulate_exit_codes_and_report(self):
        report_file = self.tmp / "report.md"
        code = self.run_cli(
            "simulate",
            "--local", str(self.conflicting_local),
            "--repo", "svc-c",
            "--compiled", str(self.instance / "dependencies" / "index.json"),
            "--report-file", str(report_file),
        )
        self.assertEqual(code, 2)  # new conflicts
        text = report_file.read_text()
        self.assertIn("dependency pre-merge simulation", text)
        self.assertIn("ownership-dispute", text)
        self.assertIn("panopticon-dependency", text)

    def test_simulate_writes_actions_file(self):
        import json

        actions_file = self.tmp / "actions.json"
        self.run_cli(
            "simulate",
            "--local", str(self.conflicting_local),
            "--repo", "svc-c",
            "--compiled", str(self.instance / "dependencies" / "index.json"),
            "--actions-file", str(actions_file),
        )
        actions = json.loads(actions_file.read_text())
        self.assertIn({"kind": "resolve_conflict", "target": "github.com/acme/svc-a"}, actions)
        self.assertIn({"kind": "commit_and_push"}, actions)

    def test_simulate_clean_exit_zero(self):
        clean_local = self.tmp / "local_b.json"
        clean_local.write_text(dumps_index(load_fixture("local_dep_svc_b.json")))
        code = self.run_cli(
            "simulate",
            "--local", str(clean_local),
            "--repo", "svc-b",
            "--compiled", str(self.instance / "dependencies" / "index.json"),
        )
        self.assertEqual(code, 0)

    def test_simulate_operational_failure_writes_failure_section_not_crash(self):
        missing_local = self.tmp / "does_not_exist.json"
        report_file = self.tmp / "report.md"
        code = self.run_cli(
            "simulate",
            "--local", str(missing_local),
            "--repo", "svc-c",
            "--compiled", str(self.instance / "dependencies" / "index.json"),
            "--report-file", str(report_file),
        )
        self.assertNotIn(code, (0, 2))
        text = report_file.read_text()
        self.assertIn("could not run", text)

    def test_merge_writes_shard_compiled_and_json_report(self):
        json_report = self.tmp / "report.json"
        code = self.run_cli(
            "merge",
            "--local", str(self.conflicting_local),
            "--repo", "svc-c",
            "--instance-root", str(self.instance),
            "--json-report", str(json_report),
        )
        self.assertEqual(code, 2)
        self.assertTrue((self.instance / "dependencies" / "svc-c.json").exists())
        import json as _json

        report = _json.loads(json_report.read_text())
        self.assertEqual(len(report["conflicts"]["new"]), 1)


if __name__ == "__main__":
    unittest.main()
