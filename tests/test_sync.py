"""Local sync script (panopticon/sync.py): default-overwrite behavior, --check-updates dry run
(stubbed GitHub API, mirroring test_install.py's patterns), and the git-blob-sha helper's
correctness against a known `git hash-object` value."""

import contextlib
import hashlib
import json
import subprocess
import tempfile
import unittest
from io import BytesIO, StringIO
from pathlib import Path

from panopticon import bootstrap
from panopticon import sync as sync_module
from panopticon.bootstrap import LOCAL_TOOLING_MODULES, SKILLS_PREFIX
from panopticon.config import save_repo_config
from panopticon.sync import check_updates, git_blob_sha, main


def _tree_entry(path, sha, type_="blob"):
    return {"path": path, "type": type_, "sha": sha}


def _make_urlopen(routes):
    """routes: dict mapping a URL substring -> response dict (json-encoded) or bytes body."""
    def urlopen(request, timeout=30):
        url = request.full_url
        for fragment, body in routes.items():
            if fragment in url:
                if isinstance(body, (bytes, bytearray)):
                    return BytesIO(body)
                return BytesIO(json.dumps(body).encode())
        raise AssertionError(f"unexpected url: {url}")
    return urlopen


def _file_response(content_bytes):
    import base64
    return {"encoding": "base64", "content": base64.b64encode(content_bytes).decode()}


def _init_repo_config(child_root, instance="acme/instance"):
    save_repo_config(
        {"repo": "svc-a", "instance": instance, "workflow_ref": "main", "docs_location": "docs"},
        repo_root=child_root,
    )


class TestSelfContained(unittest.TestCase):
    """sync.py must never import from bootstrap.py: bootstrap.py is CI-only and is never vendored
    into a child repo, so `from .bootstrap import ...` breaks with `ModuleNotFoundError` the
    moment sync.py actually runs from its only real deployment target — a child repo that has only
    the vendored LOCAL_TOOLING_MODULES subset, not bootstrap.py (regression test: this exact
    failure was hit running `python3 -m panopticon.sync` in a bootstrapped child repo). sync.py
    duplicates the primitives it needs instead (module docstring); these tests guard against that
    duplication drifting from bootstrap.py's copies."""

    def test_does_not_import_bootstrap(self):
        import ast

        self.assertNotIn("bootstrap", sync_module.__dict__)
        tree = ast.parse(Path(sync_module.__file__).read_text(encoding="utf-8"))
        imported_modules = {
            node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        self.assertNotIn("bootstrap", imported_modules)
        self.assertNotIn("panopticon.bootstrap", imported_modules)

    def test_local_tooling_modules_matches_bootstrap(self):
        self.assertEqual(sync_module.LOCAL_TOOLING_MODULES, bootstrap.LOCAL_TOOLING_MODULES)

    def test_skills_prefix_matches_bootstrap(self):
        self.assertEqual(sync_module.SKILLS_PREFIX, bootstrap.SKILLS_PREFIX)

    def test_default_skills_location_matches_bootstrap(self):
        self.assertEqual(sync_module.DEFAULT_SKILLS_LOCATION, bootstrap.DEFAULT_SKILLS_LOCATION)

    def test_default_branch_matches_bootstrap(self):
        self.assertEqual(sync_module.DEFAULT_BRANCH, bootstrap.DEFAULT_BRANCH)

    def test_tool_locations_matches_bootstrap(self):
        self.assertEqual(sync_module.TOOL_LOCATIONS, bootstrap.TOOL_LOCATIONS)


class TestGitBlobSha(unittest.TestCase):
    def test_matches_git_hash_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.txt"
            content = b"hello world\n"
            path.write_bytes(content)
            expected = subprocess.run(
                ["git", "hash-object", str(path)], capture_output=True, text=True, check=True
            ).stdout.strip()
        self.assertEqual(git_blob_sha(content), expected)

    def test_empty_content(self):
        # Known git blob sha1 for an empty blob.
        self.assertEqual(git_blob_sha(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")


class TestCheckUpdates(unittest.TestCase):
    def test_missing_file_reported_as_would_be_created(self):
        content = b"# skill"
        sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        tree = [_tree_entry(SKILLS_PREFIX + "panopticon-foo/SKILL.md", sha)]
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_updates(tree, tmp, ".agents/skills")
        self.assertEqual(len(findings), 1)
        self.assertIn("would be created", findings[0])

    def test_matching_content_yields_no_findings(self):
        content = b"# skill"
        sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        tree = [_tree_entry(SKILLS_PREFIX + "panopticon-foo/SKILL.md", sha)]
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md"
            local.parent.mkdir(parents=True)
            local.write_bytes(content)
            findings = check_updates(tree, tmp, ".agents/skills")
        self.assertEqual(findings, [])

    def test_differing_content_reported_as_would_be_updated(self):
        content = b"# new"
        sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        tree = [_tree_entry("panopticon/docs.py", sha)]
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "panopticon" / "docs.py"
            local.parent.mkdir(parents=True)
            local.write_bytes(b"# old")
            findings = check_updates(tree, tmp, ".agents/skills")
        self.assertEqual(len(findings), 1)
        self.assertIn("would be updated", findings[0])

    def test_non_panopticon_and_unrelated_files_ignored(self):
        tree = [
            _tree_entry(".agents/skills/openspec-foo/SKILL.md", "x" * 40),
            _tree_entry("panopticon/llm.py", "y" * 40),
            _tree_entry("README.md", "z" * 40),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_updates(tree, tmp, ".agents/skills")
        self.assertEqual(findings, [])


class TestMainCheckUpdates(unittest.TestCase):
    def test_check_updates_writes_nothing(self):
        content = b"# skill"
        sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            tree_body = {"tree": [_tree_entry(SKILLS_PREFIX + "panopticon-foo/SKILL.md", sha)]}
            urlopen = _make_urlopen({"git/trees": tree_body})
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--check-updates"], env={}, child_root=tmp, urlopen=urlopen)
            created = (Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md").exists()
        self.assertEqual(code, 0)
        self.assertFalse(created)
        self.assertIn("would be created", out.getvalue())

    def test_check_updates_nothing_to_sync_reports_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            urlopen = _make_urlopen({"git/trees": {"tree": []}})
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--check-updates"], env={}, child_root=tmp, urlopen=urlopen)
        self.assertEqual(code, 0)
        self.assertIn("current", out.getvalue())

    def test_uninitialized_repo_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--check-updates"], env={}, child_root=tmp, urlopen=_make_urlopen({}))
        self.assertEqual(code, 1)
        self.assertIn("not Panopticon-initialized", out.getvalue())


class TestMainDefaultOverwrite(unittest.TestCase):
    def _router(self, skill_content=b"# panopticon-foo new", tooling_content_prefix="# "):
        skill_path = SKILLS_PREFIX + "panopticon-foo/SKILL.md"
        skill_sha = hashlib.sha1(
            f"blob {len(skill_content)}\0".encode() + skill_content
        ).hexdigest()
        tree = [_tree_entry(skill_path, skill_sha)]
        for name in LOCAL_TOOLING_MODULES:
            content = f"{tooling_content_prefix}{name}".encode()
            tree.append(_tree_entry(f"panopticon/{name}", hashlib.sha1(
                f"blob {len(content)}\0".encode() + content
            ).hexdigest()))

        def urlopen(request, timeout=30):
            url = request.full_url
            if "git/trees" in url:
                return BytesIO(json.dumps({"tree": tree}).encode())
            if f"contents/{skill_path}" in url:
                return BytesIO(json.dumps(_file_response(skill_content)).encode())
            for name in LOCAL_TOOLING_MODULES:
                if f"/contents/panopticon/{name}" in url:
                    return BytesIO(json.dumps(_file_response(f"{tooling_content_prefix}{name}".encode())).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_default_run_overwrites_drifted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            stale = Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md"
            stale.parent.mkdir(parents=True)
            stale.write_text("stale")
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main([], env={}, child_root=tmp, urlopen=self._router())
            self.assertEqual(code, 0)
            self.assertEqual(stale.read_text(), "# panopticon-foo new")
            self.assertIn("synced", out.getvalue())

    def test_default_run_vendors_all_tooling_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            out = StringIO()
            with contextlib.redirect_stdout(out):
                main([], env={}, child_root=tmp, urlopen=self._router())
            # panopticon/config.json (the repo config _init_repo_config wrote) lives alongside the
            # vendored modules in the same directory but isn't one of them.
            written = {p.name for p in (Path(tmp) / "panopticon").iterdir()}
        self.assertTrue(set(LOCAL_TOOLING_MODULES).issubset(written))

    def test_nothing_to_sync_reports_current_and_skips_download(self):
        skill_content = b"# panopticon-foo new"
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            local = Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md"
            local.parent.mkdir(parents=True)
            local.write_bytes(skill_content)
            for name in LOCAL_TOOLING_MODULES:
                (Path(tmp) / "panopticon").mkdir(exist_ok=True)
                (Path(tmp) / "panopticon" / name).write_text(f"# {name}")

            def urlopen(request, timeout=30):
                url = request.full_url
                if "git/trees" in url:
                    skill_sha = hashlib.sha1(
                        f"blob {len(skill_content)}\0".encode() + skill_content
                    ).hexdigest()
                    tree = [_tree_entry(SKILLS_PREFIX + "panopticon-foo/SKILL.md", skill_sha)]
                    for name in LOCAL_TOOLING_MODULES:
                        content = f"# {name}".encode()
                        tree.append(_tree_entry(f"panopticon/{name}", hashlib.sha1(
                            f"blob {len(content)}\0".encode() + content
                        ).hexdigest()))
                    return BytesIO(json.dumps({"tree": tree}).encode())
                raise AssertionError(f"unexpected url (no download expected): {url}")

            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main([], env={}, child_root=tmp, urlopen=urlopen)
        self.assertEqual(code, 0)
        self.assertIn("current", out.getvalue())


if __name__ == "__main__":
    unittest.main()
