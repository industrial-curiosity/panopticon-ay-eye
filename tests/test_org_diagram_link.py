"""Org-diagram link script (panopticon/org_diagram_link.py): exact URL construction, and that it
never guesses a branch when instance_default_branch is missing."""

import contextlib
import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from panopticon.config import ConfigError, save_repo_config
from panopticon.org_diagram_link import build_link, main


def _write_config(tmp, **overrides):
    config = {
        "repo": "svc-a",
        "instance": "acme/panopticon-instance",
        "instance_default_branch": "main",
        "workflow_ref": "v1",
        "docs_location": "docs",
    }
    config.update(overrides)
    save_repo_config(config, repo_root=tmp)
    return config


class TestBuildLink(unittest.TestCase):
    def test_builds_exact_url(self):
        config = {
            "repo": "svc-a",
            "instance": "acme/panopticon-instance",
            "instance_default_branch": "main",
        }
        self.assertEqual(
            build_link(config),
            "https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a",
        )

    def test_non_main_branch_used_verbatim(self):
        config = {
            "repo": "svc-b",
            "instance": "acme/panopticon-instance",
            "instance_default_branch": "trunk",
        }
        self.assertEqual(
            build_link(config),
            "https://github.com/acme/panopticon-instance/blob/trunk/docs/architecture.md#svc-b",
        )

    def test_missing_instance_default_branch_raises_not_guesses(self):
        config = {"repo": "svc-a", "instance": "acme/panopticon-instance"}
        with self.assertRaises(ConfigError) as ctx:
            build_link(config)
        self.assertIn("instance_default_branch", str(ctx.exception))


class TestMain(unittest.TestCase):
    def test_prints_exact_link_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp)
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(child_root=tmp)
        self.assertEqual(code, 0)
        self.assertEqual(
            out.getvalue().strip(),
            "https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a",
        )

    def test_uninitialized_repo_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(child_root=tmp)
        self.assertEqual(code, 1)
        self.assertIn("not Panopticon-initialized", out.getvalue())

    def test_missing_instance_default_branch_errors_without_writing_a_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "panopticon" / "config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({
                "schema_version": 1, "repo": "svc-a", "instance": "acme/panopticon-instance",
                "workflow_ref": "v1", "docs_location": "docs",
            }))
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(child_root=tmp)
        self.assertEqual(code, 1)
        self.assertIn("instance_default_branch", out.getvalue())

    def test_no_network_call_needed(self):
        # build_link/main only ever read local config — no urlopen import at all in the module, so
        # there's nothing to stub and nothing that could reach the network.
        import panopticon.org_diagram_link as module
        self.assertNotIn("urllib", dir(module))


if __name__ == "__main__":
    unittest.main()
