"""Merge core: compile reproducibility, conflict cases, simulation parity with the real merge."""

import copy
import tempfile
import unittest
from pathlib import Path

from panopticon.index import KIND_COMPILED, dumps_index, empty_index, validate_index
from panopticon.merge import (
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
        "svc-a": load_fixture("local_svc_a.json"),
        "svc-b": load_fixture("local_svc_b.json"),
    }


class TestCompile(unittest.TestCase):
    def test_union_of_consumers_and_producers(self):
        compiled = compile_index(base_shards())
        validate_index(compiled, kind=KIND_COMPILED)
        entry = compiled["interfaces"]["order-events"][0]
        self.assertEqual(entry["owner"], {"repo": "svc-a", "component": "order-service"})
        self.assertEqual([r["repo"] for r in entry["producer"]], ["svc-a"])
        self.assertEqual([r["repo"] for r in entry["consumer"]], ["svc-b"])
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
        shards["svc-c"] = load_fixture("local_svc_c_conflict.json")
        compiled = compile_index(shards)
        self.assertEqual(len(compiled["conflicts"]), 1)
        recompiled = compile_index(shards_from_compiled(compiled))
        self.assertEqual(dumps_index(compiled), dumps_index(recompiled))


class TestConflicts(unittest.TestCase):
    def test_ownership_dispute(self):
        shards = base_shards()
        shards["svc-c"] = load_fixture("local_svc_c_conflict.json")
        compiled = compile_index(shards)
        (conflict,) = compiled["conflicts"]
        self.assertEqual(conflict["reason"], "ownership-dispute")
        self.assertEqual(conflict["name"], "order-events")
        self.assertEqual([c["claimed_by"] for c in conflict["claims"]], ["svc-a", "svc-c"])
        # disputed ownership resolves to null until the dispute clears
        self.assertIsNone(compiled["interfaces"]["order-events"][0]["owner"])

    def test_owner_attribution_mismatch(self):
        shards = base_shards()
        shards["svc-b"]["interfaces"]["order-events"][0]["owner"] = {
            "repo": "svc-z",
            "component": "legacy",
        }
        compiled = compile_index(shards)
        (conflict,) = compiled["conflicts"]
        self.assertEqual(conflict["reason"], "owner-attribution-mismatch")
        # the self-claim still wins for the resolved owner
        self.assertEqual(compiled["interfaces"]["order-events"][0]["owner"]["repo"], "svc-a")

    def test_shard_replace_clears_stale_conflicts(self):
        shards = base_shards()
        shards["svc-c"] = load_fixture("local_svc_c_conflict.json")
        self.assertEqual(len(compile_index(shards)["conflicts"]), 1)
        withdrawn = load_fixture("local_svc_c_conflict.json")
        withdrawn["interfaces"]["order-events"][0]["owner"] = {
            "repo": "svc-a",
            "component": "order-service",
        }
        shards = replace_shard(shards, "svc-c", withdrawn)
        self.assertEqual(compile_index(shards)["conflicts"], [])


class TestEntryLifecycle(unittest.TestCase):
    def test_last_repo_removal_drops_object_and_key(self):
        shards = base_shards()
        local_a = load_fixture("local_svc_a.json")
        del local_a["interfaces"]["orders-api"]
        local_b = load_fixture("local_svc_b.json")
        del local_b["interfaces"]["orders-api"]
        shards = replace_shard(replace_shard(shards, "svc-a", local_a), "svc-b", local_b)
        compiled = compile_index(shards)
        self.assertNotIn("orders-api", compiled["interfaces"])
        self.assertIn("order-events", compiled["interfaces"])

    def test_type_change_creates_second_object_under_same_key(self):
        shards = base_shards()
        migrated = load_fixture("local_svc_b.json")
        migrated["interfaces"]["orders-api"][0]["type"] = "grpc"
        shards = replace_shard(shards, "svc-b", migrated)
        compiled = compile_index(shards)
        objects = compiled["interfaces"]["orders-api"]
        self.assertEqual([o["type"] for o in objects], ["grpc", "rest"])
        self.assertEqual([r["repo"] for r in objects[1]["producer"]], ["svc-a"])
        self.assertEqual([r["repo"] for r in objects[0]["consumer"]], ["svc-b"])


class TestSimulationParity(unittest.TestCase):
    def write_instance(self, tmp, shards):
        instance = Path(tmp)
        compiled = compile_index(shards)
        (instance / "interfaces").mkdir()
        for repo, shard in shards.items():
            (instance / "interfaces" / f"{repo}.json").write_text(dumps_index(shard))
        (instance / "interfaces" / "index.json").write_text(dumps_index(compiled))
        return instance, compiled

    def test_simulation_matches_real_merge(self):
        incoming = load_fixture("local_svc_c_conflict.json")
        with tempfile.TemporaryDirectory() as tmp:
            instance, compiled = self.write_instance(tmp, base_shards())
            simulated = simulate_merge(incoming, compiled, "svc-c")
            merged = merge_into_instance(instance, "svc-c", incoming)
        self.assertEqual(simulated, merged)
        self.assertEqual(len(simulated["conflicts"]["new"]), 1)
        self.assertEqual(simulated["conflicts"]["new"][0]["reason"], "ownership-dispute")

    def test_clean_simulation_reports_no_conflicts(self):
        compiled = compile_index(base_shards())
        report = simulate_merge(load_fixture("local_svc_b.json"), compiled, "svc-b")
        self.assertEqual(report["conflicts"], {"new": [], "resolved": [], "unchanged": []})
        self.assertEqual(report["added"], [])
        self.assertEqual(report["removed"], [])

    def test_merge_writes_reproducible_compiled_index(self):
        incoming = load_fixture("local_svc_c_conflict.json")
        outputs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                instance, _ = self.write_instance(tmp, base_shards())
                merge_into_instance(instance, "svc-c", incoming)
                outputs.append((instance / "interfaces" / "index.json").read_text())
        self.assertEqual(outputs[0], outputs[1])

    def test_empty_local_index_removes_shard(self):
        with tempfile.TemporaryDirectory() as tmp:
            instance, _ = self.write_instance(tmp, base_shards())
            report = merge_into_instance(instance, "svc-b", empty_index())
            self.assertFalse((instance / "interfaces" / "svc-b.json").exists())
        self.assertTrue(report["removed"] or report["changed"])


class TestDiff(unittest.TestCase):
    def test_diff_identity(self):
        compiled = compile_index(base_shards())
        report = diff_compiled(compiled, compiled, "svc-a")
        self.assertEqual(report["added"], [])
        self.assertEqual(report["removed"], [])
        self.assertEqual(report["changed"], [])


class TestCli(unittest.TestCase):
    """The `python3 -m panopticon.merge` CLI used by the CI workflows."""

    def setUp(self):
        import tempfile as _tempfile

        self._tmp = _tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.instance = self.tmp / "instance"
        shards = base_shards()
        (self.instance / "interfaces").mkdir(parents=True)
        for repo, shard in shards.items():
            (self.instance / "interfaces" / f"{repo}.json").write_text(dumps_index(shard))
        compiled = compile_index(shards)
        (self.instance / "interfaces" / "index.json").write_text(dumps_index(compiled))
        self.conflicting_local = self.tmp / "local_c.json"
        self.conflicting_local.write_text(dumps_index(load_fixture("local_svc_c_conflict.json")))

    def run_cli(self, *argv):
        import contextlib
        import io

        from panopticon.merge import main

        with contextlib.redirect_stdout(io.StringIO()):
            return main(list(argv))

    def test_simulate_exit_codes_and_report(self):
        report_file = self.tmp / "report.md"
        code = self.run_cli(
            "simulate",
            "--local", str(self.conflicting_local),
            "--repo", "svc-c",
            "--compiled", str(self.instance / "interfaces" / "index.json"),
            "--report-file", str(report_file),
        )
        self.assertEqual(code, 2)  # new conflicts
        text = report_file.read_text()
        self.assertIn("pre-merge simulation", text)
        self.assertIn("ownership-dispute", text)
        self.assertIn("panopticon-interface", text)

    def test_simulate_clean_exit_zero(self):
        clean_local = self.tmp / "local_b.json"
        clean_local.write_text(dumps_index(load_fixture("local_svc_b.json")))
        code = self.run_cli(
            "simulate",
            "--local", str(clean_local),
            "--repo", "svc-b",
            "--compiled", str(self.instance / "interfaces" / "index.json"),
        )
        self.assertEqual(code, 0)

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
        self.assertTrue((self.instance / "interfaces" / "svc-c.json").exists())
        import json as _json

        report = _json.loads(json_report.read_text())
        self.assertEqual(len(report["conflicts"]["new"]), 1)


if __name__ == "__main__":
    unittest.main()
