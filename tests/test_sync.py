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
from panopticon.bootstrap import SKILLS_PREFIX, wire_workflows
from panopticon.callers import CALLER_WORKFLOWS, caller_workflow_text
from panopticon.config import save_repo_config
from panopticon.providers import resolve_provider_contract
from panopticon.sync import _api_get, check_updates, git_blob_sha, main


ORG_CONFIG = {"llm": {"provider": "litellm"}}
LOCAL_TOOLING_MANIFEST_PATH = sync_module.LOCAL_TOOLING_MANIFEST_PATH
LOCAL_TOOLING_MANIFEST = (Path(__file__).resolve().parent.parent / LOCAL_TOOLING_MANIFEST_PATH).read_bytes()
LOCAL_TOOLING_MODULES = tuple(json.loads(LOCAL_TOOLING_MANIFEST)["modules"])


def _manifest(modules):
    return json.dumps({"schema_version": 1, "modules": list(modules)}).encode()


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
        if "contents/panopticon/callers.py" in url:
            return BytesIO(json.dumps(_file_response(Path("panopticon/callers.py").read_bytes())).encode())
        if f"contents/{LOCAL_TOOLING_MANIFEST_PATH}" in url:
            return BytesIO(json.dumps(_file_response(LOCAL_TOOLING_MANIFEST)).encode())
        if "contents/panopticon.config.json" in url:
            return BytesIO(json.dumps(_file_response(json.dumps(ORG_CONFIG).encode())).encode())
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


def _write_current_callers(child_root, contract=None):
    contract = contract or resolve_provider_contract(ORG_CONFIG["llm"])
    workflows = Path(child_root) / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    for name in CALLER_WORKFLOWS:
        (workflows / name).write_text(
            caller_workflow_text(name, "acme/instance", "main", contract, "main"),
            encoding="utf-8",
        )


class TestSelfContained(unittest.TestCase):
    """sync.py must never import from bootstrap.py: bootstrap.py is CI-only and is never vendored
    into a child repo, so `from .bootstrap import ...` breaks with `ModuleNotFoundError` the
    moment sync.py actually runs from its only real deployment target — a child repo that has only
    the vendored local-tooling subset, not bootstrap.py (regression test: this exact
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

    def test_sync_does_not_import_a_child_local_tooling_manifest(self):
        self.assertFalse(hasattr(sync_module, "LOCAL_TOOLING_MODULES"))
        entries = sync_module._tooling_tree_entries([
            _tree_entry("panopticon/llm.py", "x" * 40),
            _tree_entry("panopticon/docs.py", "y" * 40),
        ], ("docs.py",))
        self.assertEqual([entry["path"] for entry in entries], ["panopticon/docs.py"])

    def test_skills_prefix_matches_bootstrap(self):
        self.assertEqual(sync_module.SKILLS_PREFIX, bootstrap.SKILLS_PREFIX)

    def test_default_skills_location_matches_bootstrap(self):
        self.assertEqual(sync_module.DEFAULT_SKILLS_LOCATION, bootstrap.DEFAULT_SKILLS_LOCATION)

    def test_default_branch_matches_bootstrap(self):
        self.assertEqual(sync_module.DEFAULT_BRANCH, bootstrap.DEFAULT_BRANCH)

    def test_tool_locations_matches_bootstrap(self):
        self.assertEqual(sync_module.TOOL_LOCATIONS, bootstrap.TOOL_LOCATIONS)

    def test_bootstrap_and_sync_share_caller_text(self):
        contract = resolve_provider_contract(ORG_CONFIG["llm"])
        with tempfile.TemporaryDirectory() as tmp:
            wire_workflows("acme/instance", "main", contract, tmp)
            expected = caller_workflow_text(
                "panopticon-resource-sync.yml", "acme/instance", "main", contract, "main"
            )
            actual = (Path(tmp) / ".github" / "workflows" / "panopticon-resource-sync.yml").read_text()
        self.assertEqual(actual, expected)


class TestApiGetRetry(unittest.TestCase):
    def test_retry_after_is_used_for_rate_limit(self):
        from urllib.error import HTTPError

        attempts, waits = [], []

        def urlopen(request, timeout=30):
            attempts.append(1)
            if len(attempts) == 1:
                raise HTTPError(
                    request.full_url, 429, "Too Many Requests", {"Retry-After": "300"},
                    BytesIO(b"rate limited"),
                )
            return BytesIO(json.dumps({"ok": True}).encode())

        self.assertEqual(
            _api_get("https://api.github.com/repos/acme/instance", urlopen=urlopen, sleep=waits.append),
            {"ok": True},
        )
        self.assertEqual(waits, [300])

    def test_reset_time_is_capped_for_rate_limit(self):
        self.assertEqual(
            sync_module._rate_limit_delay(
                403,
                {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1000"},
                "",
                lambda: 100,
                1,
            ),
            900,
        )

    def test_rate_limit_without_headers_uses_backoff_and_exhausts(self):
        from urllib.error import HTTPError

        waits = []

        def urlopen(request, timeout=30):
            raise HTTPError(request.full_url, 429, "Too Many Requests", {}, BytesIO(b"rate limited"))

        with self.assertRaisesRegex(RuntimeError, "429"):
            _api_get(
                "https://api.github.com/repos/acme/instance", urlopen=urlopen,
                max_attempts=3, sleep=waits.append,
            )
        self.assertEqual(waits, [1, 2])


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
    def test_unmanaged_python_modules_are_classified_without_state_files(self):
        tree = [
            _tree_entry("panopticon/docs.py", "x" * 40),
            _tree_entry("panopticon/llm.py", "y" * 40),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tooling = Path(tmp) / "panopticon"
            tooling.mkdir()
            (tooling / "docs.py").write_text("managed", encoding="utf-8")
            (tooling / "llm.py").write_text("ci only", encoding="utf-8")
            (tooling / "legacy_child_module.py").write_text("child owned", encoding="utf-8")
            (tooling / "config.json").write_text("{}", encoding="utf-8")
            (tooling / "index.json").write_text("{}", encoding="utf-8")
            cache = tooling / "__pycache__"
            cache.mkdir()
            (cache / "ignored.py").write_text("cache", encoding="utf-8")
            findings = sync_module._unmanaged_tooling_findings(tree, tmp, ("docs.py",))
        self.assertEqual(
            findings,
            [
                "panopticon/legacy_child_module.py is child-only and unknown to the instance; "
                "review before removal",
                "panopticon/llm.py is instance-excluded by the local-tooling manifest; "
                "review before removal",
            ],
        )

    def test_invalid_remote_manifest_fails_with_actionable_error(self):
        def urlopen(request, timeout=30):
            return BytesIO(json.dumps(_file_response(b"this is not valid Python")).encode())

        with self.assertRaisesRegex(RuntimeError, "invalid instance local-tooling manifest JSON"):
            sync_module._remote_local_tooling_modules("acme", "instance", "main", urlopen=urlopen)

    def test_missing_file_reported_as_would_be_created(self):
        content = b"# skill"
        sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        tree = [_tree_entry(SKILLS_PREFIX + "panopticon-foo/SKILL.md", sha)]
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_updates(tree, tmp, ".agents/skills", ())
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
            findings = check_updates(tree, tmp, ".agents/skills", ())
        self.assertEqual(findings, [])

    def test_differing_content_reported_as_would_be_updated(self):
        content = b"# new"
        sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        tree = [_tree_entry("panopticon/docs.py", sha)]
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "panopticon" / "docs.py"
            local.parent.mkdir(parents=True)
            local.write_bytes(b"# old")
            findings = check_updates(tree, tmp, ".agents/skills", ("docs.py",))
        self.assertEqual(len(findings), 1)
        self.assertIn("would be updated", findings[0])

    def test_ci_only_module_is_not_managed_when_absent_from_manifest(self):
        tree = [
            _tree_entry(".agents/skills/openspec-foo/SKILL.md", "x" * 40),
            _tree_entry("panopticon/llm.py", "y" * 40),
            _tree_entry("README.md", "z" * 40),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            findings = check_updates(tree, tmp, ".agents/skills", ())
        self.assertEqual(findings, [])

    def test_tooling_directory_is_fetched_completely_before_any_file_is_written(self):
        first, second = b"first", b"second"
        tree = [
            _tree_entry("panopticon/first.py", git_blob_sha(first)),
            _tree_entry("panopticon/second.py", git_blob_sha(second)),
        ]

        def urlopen(request, timeout=30):
            if "first.py" in request.full_url:
                return BytesIO(json.dumps(_file_response(first)).encode())
            raise RuntimeError("second file unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "second file unavailable"):
                sync_module.download_local_tooling(
                    "acme", "instance", "main", tree, ("first.py", "second.py"),
                    child_root=tmp, urlopen=urlopen
                )
            self.assertFalse((Path(tmp) / "panopticon" / "first.py").exists())


class TestMainCheckUpdates(unittest.TestCase):
    def test_check_updates_writes_nothing(self):
        content = b"# skill"
        sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        manifest = _manifest(("docs.py",))
        manifest_sha = git_blob_sha(manifest)
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            tree_body = {"tree": [
                _tree_entry(SKILLS_PREFIX + "panopticon-foo/SKILL.md", sha),
                _tree_entry("panopticon/docs.py", manifest_sha),
            ]}
            urlopen = _make_urlopen({
                "git/trees": tree_body,
                f"contents/{LOCAL_TOOLING_MANIFEST_PATH}": _file_response(manifest),
            })
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--check-updates"], env={}, child_root=tmp, urlopen=urlopen)
            created = (Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md").exists()
        self.assertEqual(code, 0)
        self.assertFalse(created)
        self.assertIn("would be created", out.getvalue())

    def test_check_updates_nothing_to_sync_reports_current(self):
        manifest = _manifest(("docs.py",))
        docs = b"# current docs\n"
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            _write_current_callers(tmp)
            local_manifest = Path(tmp) / "panopticon" / "local-tooling.json"
            local_manifest.write_bytes(manifest)
            (Path(tmp) / "panopticon" / "docs.py").write_bytes(docs)
            urlopen = _make_urlopen({
                "git/trees": {"tree": [
                    _tree_entry("panopticon/docs.py", git_blob_sha(docs)),
                ]},
                f"contents/{LOCAL_TOOLING_MANIFEST_PATH}": _file_response(manifest),
            })
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

    def test_check_updates_uses_the_remote_manifest_not_the_child_copy(self):
        manifest = _manifest(("docs.py",))
        docs = b"# current instance docs\n"
        llm = b"# ci only\n"
        tree = [
            _tree_entry("panopticon/docs.py", git_blob_sha(docs)),
            _tree_entry("panopticon/llm.py", git_blob_sha(llm)),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            local_manifest = Path(tmp) / "panopticon" / "local-tooling.json"
            local_manifest.write_bytes(_manifest(("llm.py",)))
            urlopen = _make_urlopen({
                "git/trees": {"tree": tree},
                f"contents/{LOCAL_TOOLING_MANIFEST_PATH}": _file_response(manifest),
            })
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--check-updates"], env={}, child_root=tmp, urlopen=urlopen)
        self.assertEqual(code, 0)
        self.assertIn("panopticon/docs.py would be created", out.getvalue())
        self.assertNotIn("panopticon/llm.py", out.getvalue())

    def test_check_updates_warns_about_unmanaged_modules_without_writing_them(self):
        manifest = _manifest(("docs.py",))
        docs = b"# current instance docs\n"
        llm = b"# ci only\n"
        tree = [
            _tree_entry("panopticon/docs.py", git_blob_sha(docs)),
            _tree_entry("panopticon/llm.py", git_blob_sha(llm)),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            legacy = Path(tmp) / "panopticon" / "legacy_child_module.py"
            excluded = Path(tmp) / "panopticon" / "llm.py"
            legacy.write_text("keep child file", encoding="utf-8")
            excluded.write_text("keep ci module", encoding="utf-8")
            urlopen = _make_urlopen({
                "git/trees": {"tree": tree},
                f"contents/{LOCAL_TOOLING_MANIFEST_PATH}": _file_response(manifest),
            })
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--check-updates"], env={}, child_root=tmp, urlopen=urlopen)
            self.assertEqual(code, 0)
            self.assertEqual(legacy.read_text(encoding="utf-8"), "keep child file")
            self.assertEqual(excluded.read_text(encoding="utf-8"), "keep ci module")
        self.assertIn("legacy_child_module.py is child-only", out.getvalue())
        self.assertIn("llm.py is instance-excluded", out.getvalue())

    def test_invalid_instance_provider_configuration_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            urlopen = _make_urlopen({
                "contents/panopticon.config.json": _file_response(b'{"llm": {}}'),
            })
            code = main([], env={}, child_root=tmp, urlopen=urlopen)
        self.assertEqual(code, 1)


class TestMainDefaultOverwrite(unittest.TestCase):
    def _router(self, skill_content=b"# panopticon-foo new", tooling_content_prefix="# ",
                org_config=ORG_CONFIG):
        skill_path = SKILLS_PREFIX + "panopticon-foo/SKILL.md"
        skill_sha = hashlib.sha1(
            f"blob {len(skill_content)}\0".encode() + skill_content
        ).hexdigest()
        tree = [_tree_entry(skill_path, skill_sha)]
        source_files = {}
        for name in LOCAL_TOOLING_MODULES:
            content = (
                Path("panopticon/callers.py").read_bytes()
                if name == "callers.py"
                else f"{tooling_content_prefix}{name}".encode()
            )
            source_files[name] = content
            tree.append(_tree_entry(f"panopticon/{name}", hashlib.sha1(
                f"blob {len(content)}\0".encode() + content
            ).hexdigest()))

        def urlopen(request, timeout=30):
            url = request.full_url
            if "git/trees" in url:
                return BytesIO(json.dumps({"tree": tree}).encode())
            if "contents/panopticon.config.json" in url:
                return BytesIO(json.dumps(_file_response(json.dumps(org_config).encode())).encode())
            if f"contents/{LOCAL_TOOLING_MANIFEST_PATH}" in url:
                return BytesIO(json.dumps(_file_response(LOCAL_TOOLING_MANIFEST)).encode())
            if f"contents/{skill_path}" in url:
                return BytesIO(json.dumps(_file_response(skill_content)).encode())
            for name in LOCAL_TOOLING_MODULES:
                if f"/contents/panopticon/{name}" in url:
                    return BytesIO(json.dumps(_file_response(source_files[name])).encode())
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

    def test_default_run_vendors_the_instance_manifest_modules(self):
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
            _write_current_callers(tmp)
            local = Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md"
            local.parent.mkdir(parents=True)
            local.write_bytes(skill_content)
            for name in LOCAL_TOOLING_MODULES:
                (Path(tmp) / "panopticon").mkdir(exist_ok=True)
                content = f"# {name}"
                (Path(tmp) / "panopticon" / name).write_text(content, encoding="utf-8")

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
                if "contents/panopticon.config.json" in url:
                    return BytesIO(json.dumps(_file_response(json.dumps(ORG_CONFIG).encode())).encode())
                if f"contents/{LOCAL_TOOLING_MANIFEST_PATH}" in url:
                    return BytesIO(json.dumps(_file_response(LOCAL_TOOLING_MANIFEST)).encode())
                raise AssertionError(f"unexpected url (no download expected): {url}")

            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main([], env={}, child_root=tmp, urlopen=urlopen)
        self.assertEqual(code, 0)
        self.assertIn("current", out.getvalue())

    def test_default_run_creates_missing_resource_sync_caller(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            code = main([], env={}, child_root=tmp, urlopen=self._router())
            path = Path(tmp) / ".github" / "workflows" / "panopticon-resource-sync.yml"
            self.assertEqual(code, 0)
            self.assertIn("shared-child-resource-sync.yml@main", path.read_text())

    def test_sync_preserves_protected_and_child_owned_files_without_deleting_legacy_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            root = Path(tmp)
            config = root / "panopticon" / "config.json"
            legacy = root / "panopticon" / "legacy-child-module.py"
            workflow = root / ".github" / "workflows" / "child-owned.yml"
            legacy.write_text("keep me", encoding="utf-8")
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text("name: child owned\n", encoding="utf-8")

            self.assertEqual(main([], env={}, child_root=tmp, urlopen=self._router()), 0)

            self.assertEqual(json.loads(config.read_text())["repo"], "svc-a")
            self.assertEqual(legacy.read_text(encoding="utf-8"), "keep me")
            self.assertEqual(workflow.read_text(encoding="utf-8"), "name: child owned\n")

    def test_check_updates_reports_missing_caller_without_creating_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--check-updates"], env={}, child_root=tmp, urlopen=self._router())
            path = Path(tmp) / ".github" / "workflows" / "panopticon-resource-sync.yml"
            self.assertEqual(code, 0)
            self.assertFalse(path.exists())
            self.assertIn("panopticon-resource-sync.yml would be created", out.getvalue())

    def test_stale_provider_caller_is_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            path = Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml"
            path.parent.mkdir(parents=True)
            path.write_text("stale")
            self.assertEqual(main([], env={}, child_root=tmp, urlopen=self._router()), 0)
            self.assertIn("panopticon-pr-litellm.yml@main", path.read_text())

    def test_openai_configuration_generates_openai_caller(self):
        with tempfile.TemporaryDirectory() as tmp:
            _init_repo_config(tmp)
            self.assertEqual(
                main([], env={}, child_root=tmp, urlopen=self._router(org_config={"llm": {"provider": "openai"}})),
                0,
            )
            path = Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml"
            self.assertIn("panopticon-pr-openai.yml@main", path.read_text())
            self.assertNotIn("endpoint: ${{ vars.", path.read_text())


if __name__ == "__main__":
    unittest.main()
