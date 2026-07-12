"""Org-diagram link script (panopticon/org_diagram_link.py): exact URL construction, config
checked first with no network call, live fallback when the config field is missing, and that it
never guesses a branch when both config and the live lookup come up empty."""

import contextlib
import json
import tempfile
import unittest
from io import BytesIO, StringIO
from pathlib import Path
from urllib.error import HTTPError

from panopticon.config import ConfigError, save_repo_config
from panopticon.org_diagram_link import build_link, main, resolve_branch


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


def _urlopen_no_call_expected(request, timeout=30):
    raise AssertionError(f"unexpected network call: {request.full_url}")


def _make_repo_metadata_urlopen(default_branch="main", fail=False):
    def urlopen(request, timeout=30):
        if fail:
            raise HTTPError(request.full_url, 404, "Not Found", {}, BytesIO(b"{}"))
        return BytesIO(json.dumps({"default_branch": default_branch}).encode())

    return urlopen


class TestBuildLink(unittest.TestCase):
    def test_builds_exact_url(self):
        self.assertEqual(
            build_link("acme/panopticon-instance", "main", "svc-a"),
            "https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a",
        )

    def test_non_main_branch_used_verbatim(self):
        self.assertEqual(
            build_link("acme/panopticon-instance", "trunk", "svc-b"),
            "https://github.com/acme/panopticon-instance/blob/trunk/docs/architecture.md#svc-b",
        )


class TestResolveBranch(unittest.TestCase):
    def test_config_field_used_with_no_network_call(self):
        config = {"repo": "svc-a", "instance": "acme/panopticon-instance",
                  "instance_default_branch": "main"}
        branch = resolve_branch(config, env={}, urlopen=_urlopen_no_call_expected)
        self.assertEqual(branch, "main")

    def test_missing_field_falls_back_to_live_lookup(self):
        config = {"repo": "svc-a", "instance": "acme/panopticon-instance"}
        branch = resolve_branch(
            config, env={"GH_TOKEN": "tok"}, urlopen=_make_repo_metadata_urlopen("main")
        )
        self.assertEqual(branch, "main")

    def test_missing_field_and_failed_live_lookup_raises_not_guesses(self):
        config = {"repo": "svc-a", "instance": "acme/panopticon-instance"}
        with self.assertRaises(ConfigError) as ctx:
            resolve_branch(config, env={}, urlopen=_make_repo_metadata_urlopen(fail=True))
        self.assertIn("instance_default_branch", str(ctx.exception))


class TestMain(unittest.TestCase):
    def test_prints_exact_link_with_no_network_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp)
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(child_root=tmp, env={}, urlopen=_urlopen_no_call_expected)
        self.assertEqual(code, 0)
        self.assertEqual(
            out.getvalue().strip(),
            "https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a",
        )

    def test_uninitialized_repo_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(child_root=tmp, env={}, urlopen=_urlopen_no_call_expected)
        self.assertEqual(code, 1)
        self.assertIn("not Panopticon-initialized", out.getvalue())

    def test_missing_field_succeeds_via_live_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "panopticon" / "config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({
                "schema_version": 1, "repo": "svc-a", "instance": "acme/panopticon-instance",
                "workflow_ref": "v1", "docs_location": "docs",
            }))
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(
                    child_root=tmp, env={"GH_TOKEN": "tok"},
                    urlopen=_make_repo_metadata_urlopen("main"),
                )
        self.assertEqual(code, 0)
        self.assertEqual(
            out.getvalue().strip(),
            "https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a",
        )

    def test_missing_field_and_failed_live_lookup_errors_without_writing_a_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "panopticon" / "config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({
                "schema_version": 1, "repo": "svc-a", "instance": "acme/panopticon-instance",
                "workflow_ref": "v1", "docs_location": "docs",
            }))
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(
                    child_root=tmp, env={}, urlopen=_make_repo_metadata_urlopen(fail=True)
                )
        self.assertEqual(code, 1)
        self.assertIn("instance_default_branch", out.getvalue())


if __name__ == "__main__":
    unittest.main()
