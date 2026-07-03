"""Org and repo configuration: defaults, overrides in both directions, initialization flag."""

import json
import tempfile
import unittest
from pathlib import Path

from panopticon.config import (
    ConfigError,
    DEFAULT_GATING,
    gating_mode,
    load_org_config,
    load_repo_config,
    save_repo_config,
)


class TestOrgConfig(unittest.TestCase):
    def write_config(self, tmp, doc):
        (Path(tmp) / "panopticon.config.json").write_text(json.dumps(doc))

    def test_missing_file_yields_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_org_config(tmp)
        self.assertEqual(config["gating"], DEFAULT_GATING)
        self.assertEqual(config["workflow_ref"], "v1")

    def test_default_gating_policy(self):
        self.assertEqual(DEFAULT_GATING["init"], "blocking")
        self.assertEqual(DEFAULT_GATING["doc-drift"], "blocking")
        self.assertEqual(DEFAULT_GATING["interface-conflict"], "advisory")

    def test_org_can_escalate_and_downgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(
                tmp, {"gating": {"interface-conflict": "blocking", "doc-drift": "advisory"}}
            )
            config = load_org_config(tmp)
        self.assertEqual(gating_mode(config, "interface-conflict"), "blocking")
        self.assertEqual(gating_mode(config, "doc-drift"), "advisory")
        self.assertEqual(gating_mode(config, "init"), "blocking")

    def test_unknown_check_type_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"gating": {"linting": "blocking"}})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_invalid_mode_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"gating": {"init": "maybe"}})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_template_root_config_matches_defaults(self):
        repo_root = Path(__file__).resolve().parent.parent
        config = load_org_config(repo_root)
        self.assertEqual(config["gating"], DEFAULT_GATING)


class TestRepoConfig(unittest.TestCase):
    def test_uninitialized_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_repo_config(tmp))

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_repo_config(
                {
                    "repo": "svc-a",
                    "instance": "acme/panopticon-instance",
                    "workflow_ref": "v1",
                    "docs_location": "docs",
                },
                repo_root=tmp,
            )
            config = load_repo_config(tmp)
        self.assertEqual(config["repo"], "svc-a")
        self.assertEqual(config["schema_version"], 1)

    def test_incomplete_config_is_a_loud_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon"
            path.mkdir()
            (path / "config.json").write_text(json.dumps({"repo": "svc-a"}))
            with self.assertRaises(ConfigError) as ctx:
                load_repo_config(tmp)
        self.assertIn("instance", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
