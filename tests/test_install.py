"""Bootstrap installer: skill download, workflow wiring, env/prompt resolution, idempotency."""

import base64
import contextlib
import json
import os
import pty
import tempfile
import threading
import time
import unittest
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from panopticon.bootstrap import (
    CALLER_WORKFLOWS,
    DEFAULT_SKILLS_LOCATION,
    GETTING_STARTED_GUIDE,
    LOCAL_TOOLING_MODULES,
    TOOL_LOCATIONS,
    _api_get,
    _apply_key,
    _arrow_key_menu,
    _detect_existing_location,
    _resolve_typed_answer,
    agent_prompts,
    caller_workflow_text,
    candidate_locations,
    check_prerequisites,
    download_getting_started_guide,
    download_local_tooling,
    download_skills,
    fetch_org_config,
    fetch_instance_default_branch,
    manual_verification_steps,
    provider_remediation,
    refresh_instance_default_branch,
    resolve_instance,
    resolve_token,
    select_skills_location,
    sync_reminder,
    validate_provider_workflow,
    wire_workflows,
    write_local_tooling_gitignore,
)
from panopticon.bootstrap import main as bootstrap_main
from panopticon.providers import resolve_provider_contract


LITELLM_CONTRACT = resolve_provider_contract({"provider": "litellm"})
ORG_SECRETS = tuple(LITELLM_CONTRACT["secrets"].values())
ORG_VARS = tuple(LITELLM_CONTRACT["variables"].values())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_urlopen(responses):
    """Return a mock urlopen that pops successive (url_fragment, body_dict) pairs."""
    queue = list(responses)

    def urlopen(request, timeout=30):
        _, body = queue.pop(0)
        raw = json.dumps(body).encode()
        return BytesIO(raw)

    return urlopen


def _tree_entry(path, type_="blob"):
    return {"path": path, "type": type_, "sha": "abc123"}


def _file_response(content_bytes):
    return {"encoding": "base64", "content": base64.b64encode(content_bytes).decode()}


# ── Workflow generation ───────────────────────────────────────────────────────

class TestCallerWorkflowText(unittest.TestCase):
    def test_pr_workflow_references_instance_at_ref(self):
        text = caller_workflow_text(
            "panopticon-pr.yml", "acme/instance", "v1", LITELLM_CONTRACT
        )
        self.assertIn("uses: acme/instance/.github/workflows/panopticon-pr-litellm.yml@v1", text)
        self.assertNotIn("secrets: inherit", text)
        self.assertIn("api_key: ${{ secrets.PANOPTICON_LLM_API_KEY }}", text)
        self.assertIn(f"configuration_revision: {LITELLM_CONTRACT['revision']}", text)
        self.assertIn('configuration_names: \'{"api_key":"PANOPTICON_LLM_API_KEY"', text)

    def test_merge_workflow_uses_supplied_branch(self):
        text = caller_workflow_text(
            "panopticon-merge.yml", "acme/instance", "v1", LITELLM_CONTRACT, "trunk"
        )
        self.assertIn("branches: [trunk]", text)
        self.assertIn("instance_token: ${{ secrets.PANOPTICON_INSTANCE_TOKEN }}", text)

    def test_pr_close_workflow(self):
        text = caller_workflow_text(
            "panopticon-pr-close.yml", "acme/instance", "v2", LITELLM_CONTRACT
        )
        self.assertIn("types: [closed]", text)
        self.assertIn("@v2", text)


class TestWireWorkflows(unittest.TestCase):
    def test_creates_all_three_workflow_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            wire_workflows("acme/instance", "v1", LITELLM_CONTRACT, tmp)
            names = {p.name for p in (Path(tmp) / ".github" / "workflows").iterdir()}
        self.assertEqual(names, set(CALLER_WORKFLOWS))

    def test_idempotent_rerun_updates_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            wire_workflows("acme/instance", "v1", LITELLM_CONTRACT, tmp)
            wire_workflows("acme/instance", "v2", LITELLM_CONTRACT, tmp)
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
            count = len(list((Path(tmp) / ".github" / "workflows").iterdir()))
        self.assertIn("@v2", text)
        self.assertEqual(count, len(CALLER_WORKFLOWS))

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            wire_workflows("acme/instance", "v1", LITELLM_CONTRACT, tmp)
            self.assertTrue((Path(tmp) / ".github" / "workflows").is_dir())

    def test_prints_per_file_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                wire_workflows("acme/instance", "v1", LITELLM_CONTRACT, tmp)
        for i, name in enumerate(CALLER_WORKFLOWS, start=1):
            self.assertIn(f"[{i}/{len(CALLER_WORKFLOWS)}] {name}", out.getvalue())


# ── Instance slug resolution ──────────────────────────────────────────────────

class TestResolveInstance(unittest.TestCase):
    def test_reads_from_env_var(self):
        self.assertEqual(
            resolve_instance(env={"PANOPTICON_INSTANCE": "acme/instance"}),
            "acme/instance",
        )

    def test_strips_whitespace(self):
        self.assertEqual(
            resolve_instance(env={"PANOPTICON_INSTANCE": "  acme/instance  "}),
            "acme/instance",
        )

    def test_prompt_fallback_when_env_absent(self):
        result = resolve_instance(env={}, prompt_fn=lambda _: "acme/instance")
        self.assertEqual(result, "acme/instance")

    def test_invalid_slug_exits(self):
        with self.assertRaises(SystemExit):
            resolve_instance(env={"PANOPTICON_INSTANCE": "noslash"})

    def test_empty_slug_exits(self):
        with self.assertRaises(SystemExit):
            resolve_instance(env={"PANOPTICON_INSTANCE": "/"})


# ── Token resolution ──────────────────────────────────────────────────────────

class TestResolveToken(unittest.TestCase):
    def test_prefers_gh_token_env(self):
        token = resolve_token(env={"GH_TOKEN": "tok1", "GITHUB_TOKEN": "tok2"})
        self.assertEqual(token, "tok1")

    def test_falls_back_to_github_token(self):
        token = resolve_token(env={"GITHUB_TOKEN": "tok2"})
        self.assertEqual(token, "tok2")

    def test_returns_none_when_no_token(self):
        with patch("shutil.which", return_value=None):
            token = resolve_token(env={})
        self.assertIsNone(token)


# ── Skills download ───────────────────────────────────────────────────────────

class TestDownloadSkills(unittest.TestCase):
    def _make_tree_and_urlopen(self, paths):
        tree = [_tree_entry(p) for p in paths]
        responses = [
            (p, _file_response(f"# {p}".encode())) for p in paths
        ]
        return tree, _make_urlopen(responses)

    def test_downloads_skills_to_local_path(self):
        paths = [".agents/skills/panopticon-my-skill/SKILL.md"]
        tree, urlopen = self._make_tree_and_urlopen(paths)
        with tempfile.TemporaryDirectory() as tmp:
            count = download_skills("acme", "instance", "main", tree, child_root=tmp,
                                    urlopen=urlopen)
            local = Path(tmp) / ".agents" / "skills" / "panopticon-my-skill" / "SKILL.md"
            self.assertEqual(count, 1)
            self.assertTrue(local.exists())

    def test_skips_non_panopticon_skills(self):
        tree = [
            _tree_entry(".agents/skills/panopticon-doc-generation/SKILL.md"),
            _tree_entry(".agents/skills/openspec-apply-change/SKILL.md"),
            _tree_entry("panopticon/config.py"),
            _tree_entry(".github/workflows/pr.yml"),
        ]
        responses = [(".agents/skills/panopticon-doc-generation/SKILL.md",
                      _file_response(b"# panopticon-doc-generation"))]
        urlopen = _make_urlopen(responses)
        with tempfile.TemporaryDirectory() as tmp:
            count = download_skills("acme", "instance", "main", tree, child_root=tmp,
                                    urlopen=urlopen)
            excluded = Path(tmp) / ".agents" / "skills" / "openspec-apply-change"
            self.assertEqual(count, 1)
            self.assertFalse(excluded.exists())

    def test_idempotent_rerun_overwrites_existing(self):
        path = ".agents/skills/panopticon-foo/SKILL.md"
        tree = [_tree_entry(path)]
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / path
            local.parent.mkdir(parents=True)
            local.write_text("old content")
            urlopen = _make_urlopen([(path, _file_response(b"new content"))])
            download_skills("acme", "instance", "main", tree, child_root=tmp, urlopen=urlopen)
            content = local.read_text()
        self.assertEqual(content, "new content")

    def test_empty_tree_warns_and_returns_zero(self):
        tree = []
        with tempfile.TemporaryDirectory() as tmp:
            count = download_skills("acme", "instance", "main", tree, child_root=tmp,
                                    urlopen=_make_urlopen([]))
        self.assertEqual(count, 0)

    def test_writes_to_chosen_destination_location(self):
        paths = [".agents/skills/panopticon-my-skill/SKILL.md"]
        tree, urlopen = self._make_tree_and_urlopen(paths)
        with tempfile.TemporaryDirectory() as tmp:
            download_skills("acme", "instance", "main", tree, child_root=tmp,
                            dest_location=".claude/skills", urlopen=urlopen)
            at_chosen = (Path(tmp) / ".claude" / "skills" / "panopticon-my-skill" / "SKILL.md").exists()
            at_default = (Path(tmp) / ".agents" / "skills").exists()
        self.assertTrue(at_chosen)
        self.assertFalse(at_default)

    def test_prints_per_file_progress(self):
        paths = [
            ".agents/skills/panopticon-a/SKILL.md",
            ".agents/skills/panopticon-b/SKILL.md",
        ]
        tree, urlopen = self._make_tree_and_urlopen(paths)
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                download_skills("acme", "instance", "main", tree, child_root=tmp, urlopen=urlopen)
        self.assertIn("[1/2] panopticon-a/SKILL.md", out.getvalue())
        self.assertIn("[2/2] panopticon-b/SKILL.md", out.getvalue())


# ── Local tooling vendoring ──────────────────────────────────────────────────────

class TestDownloadLocalTooling(unittest.TestCase):
    def _make_urlopen(self):
        def urlopen(request, timeout=30):
            url = request.full_url
            for name in LOCAL_TOOLING_MODULES:
                if f"/contents/panopticon/{name}" in url:
                    return BytesIO(json.dumps(_file_response(f"# {name}".encode())).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_writes_all_local_tooling_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            count = download_local_tooling("acme", "instance", "main", child_root=tmp,
                                           urlopen=self._make_urlopen())
            written = {p.name for p in (Path(tmp) / "panopticon").iterdir()}
        self.assertEqual(count, len(LOCAL_TOOLING_MODULES))
        self.assertEqual(written, set(LOCAL_TOOLING_MODULES))

    def test_ci_only_modules_are_not_requested(self):
        # The stub raises AssertionError for any URL it doesn't recognize — if download_local_tooling
        # ever asked for a CI-only module (e.g. llm.py, bootstrap.py), this test would fail loudly.
        with tempfile.TemporaryDirectory() as tmp:
            download_local_tooling("acme", "instance", "main", child_root=tmp,
                                   urlopen=self._make_urlopen())

    def test_idempotent_rerun_overwrites_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "panopticon").mkdir()
            (Path(tmp) / "panopticon" / "__init__.py").write_text("stale content")
            download_local_tooling("acme", "instance", "main", child_root=tmp,
                                   urlopen=self._make_urlopen())
            content = (Path(tmp) / "panopticon" / "__init__.py").read_text()
            file_count = len(list((Path(tmp) / "panopticon").iterdir()))
        self.assertEqual(content, "# __init__.py")
        self.assertEqual(file_count, len(LOCAL_TOOLING_MODULES))

    def test_content_matches_fetched_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            download_local_tooling("acme", "instance", "main", child_root=tmp,
                                   urlopen=self._make_urlopen())
            content = (Path(tmp) / "panopticon" / "docs.py").read_text()
        self.assertEqual(content, "# docs.py")

    def test_prints_per_file_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                download_local_tooling("acme", "instance", "main", child_root=tmp,
                                       urlopen=self._make_urlopen())
        total = len(LOCAL_TOOLING_MODULES)
        for i, name in enumerate(LOCAL_TOOLING_MODULES, start=1):
            self.assertIn(f"[{i}/{total}] {name}", out.getvalue())


class TestWriteLocalToolingGitignore(unittest.TestCase):
    def test_writes_gitignore_with_pycache_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_local_tooling_gitignore(child_root=tmp)
            content = (Path(tmp) / "panopticon" / ".gitignore").read_text()
        self.assertEqual(path, Path(tmp) / "panopticon" / ".gitignore")
        self.assertEqual(content, "__pycache__/\n")

    def test_creates_panopticon_dir_if_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse((Path(tmp) / "panopticon").exists())
            write_local_tooling_gitignore(child_root=tmp)
            self.assertTrue((Path(tmp) / "panopticon").is_dir())

    def test_idempotent_rerun_overwrites_without_duplicating(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local_tooling_gitignore(child_root=tmp)
            write_local_tooling_gitignore(child_root=tmp)
            content = (Path(tmp) / "panopticon" / ".gitignore").read_text()
        self.assertEqual(content, "__pycache__/\n")


# ── Getting-started guide ────────────────────────────────────────────────────────

class TestDownloadGettingStartedGuide(unittest.TestCase):
    def _make_urlopen(self, content=b"# Panopticon\n"):
        def urlopen(request, timeout=30):
            url = request.full_url
            if f"/contents/{GETTING_STARTED_GUIDE}" in url:
                return BytesIO(json.dumps(_file_response(content)).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_downloads_guide_to_child_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            download_getting_started_guide("acme", "instance", "main", child_root=tmp,
                                           urlopen=self._make_urlopen())
            local = Path(tmp) / GETTING_STARTED_GUIDE
            self.assertTrue(local.exists())

    def test_content_matches_fetched_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            download_getting_started_guide("acme", "instance", "main", child_root=tmp,
                                           urlopen=self._make_urlopen(b"# Panopticon\nhello\n"))
            content = (Path(tmp) / GETTING_STARTED_GUIDE).read_text()
        self.assertEqual(content, "# Panopticon\nhello\n")

    def test_idempotent_rerun_overwrites_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / GETTING_STARTED_GUIDE
            local.write_text("stale content")
            download_getting_started_guide("acme", "instance", "main", child_root=tmp,
                                           urlopen=self._make_urlopen())
            content = local.read_text()
        self.assertEqual(content, "# Panopticon\n")


class TestSyncReminder(unittest.TestCase):
    def test_names_guide_location(self):
        self.assertIn(GETTING_STARTED_GUIDE, sync_reminder())

    def test_contains_sync_command(self):
        self.assertIn("python3 -m panopticon.sync", sync_reminder())

    def test_contains_check_updates_flag(self):
        self.assertIn("python3 -m panopticon.sync --check-updates", sync_reminder())


# ── instance_default_branch refresh ─────────────────────────────────────────────

def _make_repo_metadata_urlopen(default_branch="main", fail=False):
    from urllib.error import HTTPError

    def urlopen(request, timeout=30):
        if fail:
            raise HTTPError(request.full_url, 404, "Not Found", {}, BytesIO(b"{}"))
        return BytesIO(json.dumps({"default_branch": default_branch}).encode())

    return urlopen


class TestFetchInstanceDefaultBranch(unittest.TestCase):
    def test_returns_default_branch(self):
        branch = fetch_instance_default_branch(
            "acme", "instance", urlopen=_make_repo_metadata_urlopen("main")
        )
        self.assertEqual(branch, "main")

    def test_non_main_branch_returned_verbatim(self):
        branch = fetch_instance_default_branch(
            "acme", "instance", urlopen=_make_repo_metadata_urlopen("trunk")
        )
        self.assertEqual(branch, "trunk")

    def test_api_failure_returns_none(self):
        branch = fetch_instance_default_branch(
            "acme", "instance", urlopen=_make_repo_metadata_urlopen(fail=True)
        )
        self.assertIsNone(branch)


class TestRefreshInstanceDefaultBranch(unittest.TestCase):
    def test_no_config_file_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = refresh_instance_default_branch(
                "acme", "instance", child_root=tmp, urlopen=_make_repo_metadata_urlopen("main")
            )
            config_exists = (Path(tmp) / "panopticon" / "config.json").exists()
        self.assertIsNone(result)
        self.assertFalse(config_exists)

    def test_existing_config_updated_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "panopticon" / "config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({
                "schema_version": 1, "repo": "svc-a", "instance": "acme/instance",
                "workflow_ref": "v1", "docs_location": "docs",
            }))
            result = refresh_instance_default_branch(
                "acme", "instance", child_root=tmp, urlopen=_make_repo_metadata_urlopen("main")
            )
            doc = json.loads(config_path.read_text())
        self.assertEqual(result, "main")
        self.assertEqual(doc["instance_default_branch"], "main")
        # every other field is untouched
        self.assertEqual(doc["repo"], "svc-a")
        self.assertEqual(doc["workflow_ref"], "v1")
        self.assertEqual(doc["docs_location"], "docs")

    def test_failed_resolution_leaves_config_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "panopticon" / "config.json"
            config_path.parent.mkdir(parents=True)
            original = {
                "schema_version": 1, "repo": "svc-a", "instance": "acme/instance",
                "workflow_ref": "v1", "docs_location": "docs",
            }
            config_path.write_text(json.dumps(original))
            result = refresh_instance_default_branch(
                "acme", "instance", child_root=tmp, urlopen=_make_repo_metadata_urlopen(fail=True)
            )
            doc = json.loads(config_path.read_text())
        self.assertIsNone(result)
        self.assertEqual(doc, original)


# ── Prerequisite check ────────────────────────────────────────────────────────

class TestCheckPrerequisites(unittest.TestCase):
    def _make_urlopen_for_prereqs(self, secrets, variables):
        def urlopen(request, timeout=30):
            url = request.full_url
            if "secrets" in url:
                body = {"secrets": [{"name": n} for n in secrets]}
            else:
                body = {"variables": [{"name": n} for n in variables]}
            return BytesIO(json.dumps(body).encode())
        return urlopen

    def test_all_present_returns_empty_report(self):
        urlopen = self._make_urlopen_for_prereqs(ORG_SECRETS, ORG_VARS)
        report = check_prerequisites("acme", LITELLM_CONTRACT, token="tok", urlopen=urlopen)
        self.assertEqual(report, [])

    def test_missing_secret_reported(self):
        urlopen = self._make_urlopen_for_prereqs(["PANOPTICON_LLM_API_KEY"], list(ORG_VARS))
        report = check_prerequisites("acme", LITELLM_CONTRACT, token="tok", urlopen=urlopen)
        text = "\n".join(report)
        self.assertIn("PANOPTICON_INSTANCE_TOKEN", text)

    def test_missing_variable_reported(self):
        urlopen = self._make_urlopen_for_prereqs(list(ORG_SECRETS), ["PANOPTICON_LLM_MODEL"])
        report = check_prerequisites("acme", LITELLM_CONTRACT, token="tok", urlopen=urlopen)
        text = "\n".join(report)
        self.assertIn("PANOPTICON_LLM_ENDPOINT", text)

    def test_api_failure_reported_non_blocking(self):
        def urlopen(request, timeout=30):
            from urllib.error import HTTPError
            raise HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(b"denied"))
        report = check_prerequisites("acme", LITELLM_CONTRACT, token="tok", urlopen=urlopen)
        self.assertTrue(len(report) > 0)
        self.assertIn("could not verify", "\n".join(report))

    def test_no_token_returns_manual_steps_without_calling_api(self):
        def urlopen(request, timeout=30):
            raise AssertionError("should not call the API when no token is available")
        report = check_prerequisites("acme", LITELLM_CONTRACT, token=None, urlopen=urlopen)
        text = "\n".join(report)
        for name in (*ORG_SECRETS, *ORG_VARS):
            self.assertIn(name, text)
        self.assertIn("gh secret list --org acme", text)
        self.assertIn("gh variable list --org acme", text)
        self.assertIn("github.com/organizations/acme/settings/secrets/actions", text)

    def test_no_token_manual_steps_not_framed_as_error(self):
        report = manual_verification_steps("acme", LITELLM_CONTRACT)
        text = "\n".join(report)
        self.assertNotIn("error", text.lower())
        self.assertNotIn("fail", text.lower())


# ── _api_get retry behavior ─────────────────────────────────────────────────────

class TestApiGetRetry(unittest.TestCase):
    def _recording_sleep(self):
        calls = []
        return calls, calls.append

    def test_transient_error_retried_and_succeeds(self):
        from urllib.error import HTTPError

        attempts = []

        def urlopen(request, timeout=30):
            attempts.append(1)
            if len(attempts) < 2:
                raise HTTPError(request.full_url, 502, "Bad Gateway", {}, BytesIO(b"<html>Unicorn!</html>"))
            return BytesIO(json.dumps({"ok": True}).encode())

        calls, sleep = self._recording_sleep()
        result = _api_get("https://api.github.com/repos/acme/instance", urlopen=urlopen, sleep=sleep)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(attempts), 2)
        self.assertEqual(calls, [1])  # one backoff between attempt 1 and 2

    def test_retries_exhausted_raises_with_status_and_body(self):
        from urllib.error import HTTPError

        def urlopen(request, timeout=30):
            raise HTTPError(request.full_url, 503, "Service Unavailable", {}, BytesIO(b"down"))

        calls, sleep = self._recording_sleep()
        with self.assertRaises(RuntimeError) as ctx:
            _api_get("https://api.github.com/repos/acme/instance", urlopen=urlopen, max_attempts=3, sleep=sleep)
        self.assertIn("503", str(ctx.exception))
        self.assertIn("down", str(ctx.exception))
        self.assertEqual(calls, [1, 2])  # backoff after attempts 1 and 2, none after the last

    def test_non_transient_error_fails_without_retrying(self):
        from urllib.error import HTTPError

        attempts = []

        def urlopen(request, timeout=30):
            attempts.append(1)
            raise HTTPError(request.full_url, 404, "Not Found", {}, BytesIO(b"missing"))

        calls, sleep = self._recording_sleep()
        with self.assertRaises(RuntimeError) as ctx:
            _api_get("https://api.github.com/repos/acme/instance", urlopen=urlopen, sleep=sleep)
        self.assertIn("404", str(ctx.exception))
        self.assertEqual(len(attempts), 1)
        self.assertEqual(calls, [])

    def test_connection_error_retried(self):
        from urllib.error import URLError

        attempts = []

        def urlopen(request, timeout=30):
            attempts.append(1)
            if len(attempts) < 2:
                raise URLError("connection reset")
            return BytesIO(json.dumps({"ok": True}).encode())

        calls, sleep = self._recording_sleep()
        result = _api_get("https://api.github.com/repos/acme/instance", urlopen=urlopen, sleep=sleep)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls, [1])


# ── workflow_ref default resolution (main) ─────────────────────────────────────

class TestMainWorkflowRefDefault(unittest.TestCase):
    def _router(self, org_config_content=None, secrets=ORG_SECRETS, variables=ORG_VARS):
        from urllib.error import HTTPError

        def urlopen(request, timeout=30):
            url = request.full_url
            if "contents/panopticon.config.json" in url:
                if org_config_content is None:
                    raise HTTPError(url, 404, "Not Found", {}, BytesIO(b"{}"))
                return BytesIO(json.dumps(_file_response(org_config_content)).encode())
            if "git/trees" in url:
                return BytesIO(
                    json.dumps(
                        {"tree": [_tree_entry(".github/workflows/panopticon-pr-litellm.yml")]}
                    ).encode()
                )
            for name in LOCAL_TOOLING_MODULES:
                if f"/contents/panopticon/{name}" in url:
                    return BytesIO(json.dumps(_file_response(f"# {name}".encode())).encode())
            if f"contents/{GETTING_STARTED_GUIDE}" in url:
                return BytesIO(json.dumps(_file_response(b"# Panopticon")).encode())
            if "actions/secrets" in url:
                return BytesIO(json.dumps({"secrets": [{"name": n} for n in secrets]}).encode())
            if "actions/variables" in url:
                return BytesIO(json.dumps({"variables": [{"name": n} for n in variables]}).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_no_org_config_fails_before_writing_with_complete_remediation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = bootstrap_main(
                    env={
                        "PANOPTICON_INSTANCE": "acme/instance",
                        "GH_TOKEN": "tok",
                        "PANOPTICON_SKILLS_LOCATION": ".agents/skills",
                    },
                    child_root=tmp,
                    urlopen=self._router(org_config_content=b'{"schema_version": 1}'),
                )
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual(code, 1)
        self.assertIn("actions/workflows/configure-panopticon.yml", out.getvalue())
        self.assertIn("gh workflow run configure-panopticon.yml --repo acme/instance", out.getvalue())
        self.assertIn(
            "| PANOPTICON_INSTANCE='acme/instance' python3", out.getvalue()
        )
        self.assertNotIn("export PANOPTICON_INSTANCE", out.getvalue())

    def test_org_config_workflow_ref_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={
                    "PANOPTICON_INSTANCE": "acme/instance",
                    "GH_TOKEN": "tok",
                    "PANOPTICON_SKILLS_LOCATION": ".agents/skills",
                },
                child_root=tmp,
                urlopen=self._router(
                    org_config_content=json.dumps(
                        {"workflow_ref": "v2", "llm": {"provider": "litellm"}}
                    ).encode()
                ),
            )
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
        self.assertEqual(code, 0)
        self.assertIn("uses: acme/instance/.github/workflows/panopticon-pr-litellm.yml@v2", text)


class TestProviderBootstrapErrors(unittest.TestCase):
    def test_provider_change_changes_revision_and_remote_workflow(self):
        litellm = resolve_provider_contract({"provider": "litellm"})
        bedrock = resolve_provider_contract({"provider": "bedrock"})
        litellm_text = caller_workflow_text(
            "panopticon-pr.yml", "acme/instance", "release", litellm
        )
        bedrock_text = caller_workflow_text(
            "panopticon-pr.yml", "acme/instance", "release", bedrock
        )
        self.assertNotEqual(litellm["revision"], bedrock["revision"])
        self.assertIn("panopticon-pr-litellm.yml@release", litellm_text)
        self.assertIn("panopticon-pr-bedrock.yml@release", bedrock_text)

    def test_configured_name_change_updates_revision_and_explicit_mapping(self):
        original = resolve_provider_contract({"provider": "litellm"})
        renamed = resolve_provider_contract(
            {
                "provider": "litellm",
                "secrets": {"api_key": "ACME_LLM_KEY"},
            }
        )
        text = caller_workflow_text(
            "panopticon-pr.yml", "acme/instance", "release", renamed
        )
        self.assertNotEqual(original["revision"], renamed["revision"])
        self.assertIn("api_key: ${{ secrets.ACME_LLM_KEY }}", text)

    def test_bedrock_caller_uses_custom_names_and_oidc_permissions(self):
        contract = resolve_provider_contract(
            {
                "provider": "bedrock",
                "secrets": {"instance_token": "ACME_INSTANCE_TOKEN"},
                "variables": {
                    "aws_region": "ACME_AWS_REGION",
                    "aws_role_arn": "ACME_BEDROCK_ROLE",
                    "model": "ACME_BEDROCK_MODEL",
                },
            }
        )
        text = caller_workflow_text(
            "panopticon-pr.yml", "acme/instance", "release", contract
        )
        self.assertIn("panopticon-pr-bedrock.yml@release", text)
        self.assertIn("id-token: write", text)
        self.assertIn("aws_region: ${{ vars.ACME_AWS_REGION }}", text)
        self.assertIn("instance_token: ${{ secrets.ACME_INSTANCE_TOKEN }}", text)
        self.assertNotIn("api_key:", text)
        self.assertNotIn("secrets: inherit", text)

    def test_missing_selected_workflow_is_a_loud_prewrite_error(self):
        with self.assertRaisesRegex(RuntimeError, "panopticon-pr-bedrock.yml"):
            validate_provider_workflow(
                [],
                resolve_provider_contract({"provider": "bedrock"}),
                "acme/instance",
                "v2",
            )

    def test_missing_instance_managed_action_is_a_loud_prewrite_error(self):
        contract = resolve_provider_contract(
            {"provider": "bedrock", "credential_mode": "instance-managed"}
        )
        tree = [{"type": "blob", "path": ".github/workflows/panopticon-pr-bedrock.yml"}]
        with self.assertRaisesRegex(RuntimeError, "instance-managed credential action"):
            validate_provider_workflow(tree, contract, "acme/instance", "v2")

    def test_missing_instance_managed_action_prints_custom_ref_recovery(self):
        def urlopen(request, timeout=30):
            url = request.full_url
            if "contents/panopticon.config.json" in url:
                return BytesIO(
                    json.dumps(
                        _file_response(
                            json.dumps(
                                {
                                    "workflow_ref": "release/2026-07",
                                    "llm": {
                                        "provider": "bedrock",
                                        "credential_mode": "instance-managed",
                                    },
                                }
                            ).encode()
                        )
                    ).encode()
                )
            if "git/trees/release/2026-07" in url:
                return BytesIO(
                    json.dumps(
                        {
                            "tree": [
                                _tree_entry(".github/workflows/panopticon-pr-bedrock.yml"),
                            ]
                        }
                    ).encode()
                )
            raise AssertionError(f"unexpected URL: {url}")

        with tempfile.TemporaryDirectory() as tmp:
            output = StringIO()
            with contextlib.redirect_stdout(output):
                code = bootstrap_main(
                    env={
                        "PANOPTICON_INSTANCE": "acme/private-instance",
                        "PANOPTICON_SKILLS_LOCATION": ".agents/skills",
                    },
                    child_root=tmp,
                    urlopen=urlopen,
                )
            self.assertEqual(list(Path(tmp).iterdir()), [])

        self.assertEqual(code, 1)
        self.assertIn("workflow_ref: release/2026-07", output.getvalue())
        self.assertIn("instance-managed credential action", output.getvalue())
        self.assertIn(
            "curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/"
            "panopticon-ay-eye/main/install.py | "
            "PANOPTICON_INSTANCE='acme/private-instance' python3",
            output.getvalue(),
        )

    def test_fetch_org_config_preserves_access_failure(self):
        from urllib.error import HTTPError

        def urlopen(request, timeout=30):
            raise HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(b"denied"))

        with self.assertRaisesRegex(RuntimeError, "403"):
            fetch_org_config("acme", "instance", "main", token="tok", urlopen=urlopen)

    def test_fetch_org_config_reports_invalid_encoded_content(self):
        def urlopen(request, timeout=30):
            return BytesIO(
                json.dumps({"encoding": "base64", "content": "//4="}).encode()
            )

        with self.assertRaisesRegex(RuntimeError, "invalid panopticon.config.json"):
            fetch_org_config("acme", "instance", "main", urlopen=urlopen)

    def test_provider_remediation_has_ordered_console_and_cli_instructions(self):
        text = provider_remediation("acme/instance", "trunk")
        self.assertIn("1. Open https://github.com/acme/instance/actions/workflows/", text)
        self.assertIn("3. Select branch trunk", text)
        self.assertIn("gh workflow run configure-panopticon.yml --repo acme/instance --ref trunk", text)
        self.assertIn("wait for the green completed run", text)
        self.assertIn(
            "| PANOPTICON_INSTANCE='acme/instance' python3",
            text,
        )


# ── Skills location selection ───────────────────────────────────────────────────

class TestCandidateLocations(unittest.TestCase):
    def test_default_is_first(self):
        self.assertEqual(candidate_locations()[0], DEFAULT_SKILLS_LOCATION)

    def test_deduplicated_across_tools(self):
        locations = candidate_locations()
        self.assertEqual(len(locations), len(set(locations)))

    def test_includes_claude_specific_location(self):
        self.assertIn(".claude/skills", candidate_locations())

    def test_matches_union_of_tool_locations(self):
        expected = {loc for _, locs in TOOL_LOCATIONS.values() for loc in locs}
        self.assertEqual(set(candidate_locations()), expected)


class TestDetectExistingLocation(unittest.TestCase):
    def test_returns_none_when_nothing_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _detect_existing_location(tmp)
        self.assertIsNone(result)

    def test_detects_populated_non_default_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".claude" / "skills" / "panopticon-foo").mkdir(parents=True)
            result = _detect_existing_location(tmp)
        self.assertEqual(result, ".claude/skills")

    def test_ignores_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".claude" / "skills").mkdir(parents=True)
            result = _detect_existing_location(tmp)
        self.assertIsNone(result)


class TestResolveTypedAnswer(unittest.TestCase):
    def setUp(self):
        self.locations = [".agents/skills", ".claude/skills", ".cursor/skills"]

    def test_blank_answer_is_default(self):
        self.assertEqual(_resolve_typed_answer("", self.locations), ".agents/skills")

    def test_number_selects_by_index(self):
        self.assertEqual(_resolve_typed_answer("2", self.locations), ".claude/skills")

    def test_out_of_range_number_falls_back_to_default(self):
        self.assertEqual(_resolve_typed_answer("99", self.locations), ".agents/skills")

    def test_literal_path_is_used_verbatim(self):
        self.assertEqual(_resolve_typed_answer(".opencode/skills", self.locations), ".opencode/skills")

    def test_trailing_slash_is_stripped(self):
        self.assertEqual(_resolve_typed_answer(".opencode/skills/", self.locations), ".opencode/skills")


class TestApplyKey(unittest.TestCase):
    def test_enter_confirms(self):
        self.assertEqual(_apply_key(0, 3, b"\r"), (0, True))
        self.assertEqual(_apply_key(1, 3, b"\n"), (1, True))

    def test_down_arrow_advances(self):
        self.assertEqual(_apply_key(0, 3, b"\x1b[B"), (1, False))

    def test_down_arrow_wraps(self):
        self.assertEqual(_apply_key(2, 3, b"\x1b[B"), (0, False))

    def test_up_arrow_retreats(self):
        self.assertEqual(_apply_key(1, 3, b"\x1b[A"), (0, False))

    def test_up_arrow_wraps(self):
        self.assertEqual(_apply_key(0, 3, b"\x1b[A"), (2, False))

    def test_unknown_key_is_ignored(self):
        self.assertEqual(_apply_key(1, 3, b"q"), (1, False))


class TestArrowKeyMenu(unittest.TestCase):
    """Exercises the real raw-terminal-mode menu against a pseudo-terminal pair — not a mock."""

    def test_down_then_enter_selects_second_option(self):
        master_fd, slave_fd = pty.openpty()
        slave_path = os.ttyname(slave_fd)
        os.close(slave_fd)

        def feeder():
            time.sleep(0.05)
            os.write(master_fd, b"\x1b[B\r")

        thread = threading.Thread(target=feeder)
        thread.start()
        try:
            result = _arrow_key_menu(
                [".agents/skills", ".claude/skills", ".cursor/skills"],
                default_index=0,
                tty_path=slave_path,
            )
        finally:
            thread.join()
            os.close(master_fd)
        self.assertEqual(result, 1)

    def test_unavailable_tty_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = str(Path(tmp) / "no-such-tty")
            result = _arrow_key_menu([".agents/skills"], tty_path=missing_path)
        self.assertIsNone(result)


class TestSelectSkillsLocation(unittest.TestCase):
    def test_env_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = select_skills_location(env={"PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                                            child_root=tmp)
        self.assertEqual(result, ".claude/skills")

    def test_env_override_strips_trailing_slash(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = select_skills_location(env={"PANOPTICON_SKILLS_LOCATION": ".claude/skills/"},
                                            child_root=tmp)
        self.assertEqual(result, ".claude/skills")

    def test_reuses_existing_location_without_prompting(self):
        def no_prompt(_):
            raise AssertionError("must not prompt when a location is already populated")

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".cursor" / "skills" / "panopticon-foo").mkdir(parents=True)
            result = select_skills_location(env={}, prompt_fn=no_prompt, child_root=tmp)
        self.assertEqual(result, ".cursor/skills")

    def test_prompt_fn_injection_used_for_typed_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = select_skills_location(env={}, prompt_fn=lambda _: "2", child_root=tmp)
        self.assertEqual(result, candidate_locations()[1])

    def test_prompt_fn_blank_answer_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = select_skills_location(env={}, prompt_fn=lambda _: "", child_root=tmp)
        self.assertEqual(result, DEFAULT_SKILLS_LOCATION)

    def test_no_interactive_input_defaults_without_blocking(self):
        # No prompt_fn, no env override, no existing location: falls through arrow-key menu and
        # typed-tty-prompt (both fail without a real terminal) to the plain default.
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.stdin.isatty", return_value=False):
                result = select_skills_location(env={}, child_root=tmp)
        self.assertEqual(result, DEFAULT_SKILLS_LOCATION)


class TestMainSkillsLocationFlow(unittest.TestCase):
    def _router(self):
        from urllib.error import HTTPError

        skill_path = ".agents/skills/panopticon-foo/SKILL.md"

        def urlopen(request, timeout=30):
            url = request.full_url
            if "contents/panopticon.config.json" in url:
                return BytesIO(
                    json.dumps(
                        _file_response(
                            json.dumps({"llm": {"provider": "litellm"}}).encode()
                        )
                    ).encode()
                )
            if "git/trees" in url:
                return BytesIO(
                    json.dumps(
                        {
                            "tree": [
                                _tree_entry(skill_path),
                                _tree_entry(
                                    ".github/workflows/panopticon-pr-litellm.yml"
                                ),
                            ]
                        }
                    ).encode()
                )
            if "contents/" + skill_path in url:
                return BytesIO(json.dumps(_file_response(b"# panopticon-foo")).encode())
            for name in LOCAL_TOOLING_MODULES:
                if f"/contents/panopticon/{name}" in url:
                    return BytesIO(json.dumps(_file_response(f"# {name}".encode())).encode())
            if f"contents/{GETTING_STARTED_GUIDE}" in url:
                return BytesIO(json.dumps(_file_response(b"# Panopticon")).encode())
            if "actions/secrets" in url:
                return BytesIO(json.dumps({"secrets": [{"name": n} for n in ORG_SECRETS]}).encode())
            if "actions/variables" in url:
                return BytesIO(json.dumps({"variables": [{"name": n} for n in ORG_VARS]}).encode())
            if url == "https://api.github.com/repos/acme/instance":
                return BytesIO(json.dumps({"default_branch": "main"}).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_location_chosen_before_any_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={
                    "PANOPTICON_INSTANCE": "acme/instance",
                    "GH_TOKEN": "tok",
                    "PANOPTICON_SKILLS_LOCATION": ".claude/skills",
                },
                child_root=tmp,
                urlopen=self._router(),
            )
            at_chosen = (Path(tmp) / ".claude" / "skills" / "panopticon-foo" / "SKILL.md").exists()
            agents_dir_exists = (Path(tmp) / ".agents").exists()
        self.assertEqual(code, 0)
        self.assertTrue(at_chosen)
        self.assertFalse(agents_dir_exists)

    def test_local_tooling_vendored_alongside_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={
                    "PANOPTICON_INSTANCE": "acme/instance",
                    "GH_TOKEN": "tok",
                    "PANOPTICON_SKILLS_LOCATION": ".claude/skills",
                },
                child_root=tmp,
                urlopen=self._router(),
            )
            vendored = {p.name for p in (Path(tmp) / "panopticon").iterdir()}
        self.assertEqual(code, 0)
        self.assertEqual(vendored, set(LOCAL_TOOLING_MODULES) | {".gitignore"})

    def test_default_location_used_without_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.stdin.isatty", return_value=False):
                code = bootstrap_main(
                    env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok"},
                    child_root=tmp,
                    urlopen=self._router(),
                )
            agents_skills_exists = (
                Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md"
            ).exists()
        self.assertEqual(code, 0)
        self.assertTrue(agents_skills_exists)

    def test_getting_started_guide_downloaded_on_first_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok",
                     "PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                child_root=tmp,
                urlopen=self._router(),
            )
            guide_exists = (Path(tmp) / GETTING_STARTED_GUIDE).exists()
        self.assertEqual(code, 0)
        self.assertTrue(guide_exists)

    def test_getting_started_guide_overwritten_on_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / GETTING_STARTED_GUIDE).write_text("stale content")
            code = bootstrap_main(
                env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok",
                     "PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                child_root=tmp,
                urlopen=self._router(),
            )
            content = (Path(tmp) / GETTING_STARTED_GUIDE).read_text()
            guide_count = len(list(Path(tmp).glob(f"{GETTING_STARTED_GUIDE}*")))
        self.assertEqual(code, 0)
        self.assertEqual(content, "# Panopticon")
        self.assertEqual(guide_count, 1)

    def test_output_names_guide_and_sync_command_on_first_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = bootstrap_main(
                    env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok",
                         "PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                    child_root=tmp,
                    urlopen=self._router(),
                )
        self.assertEqual(code, 0)
        self.assertIn(GETTING_STARTED_GUIDE, out.getvalue())
        self.assertIn("python3 -m panopticon.sync", out.getvalue())

    def test_output_names_guide_and_sync_command_on_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            bootstrap_main(
                env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok",
                     "PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                child_root=tmp,
                urlopen=self._router(),
            )
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = bootstrap_main(
                    env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok",
                         "PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                    child_root=tmp,
                    urlopen=self._router(),
                )
        self.assertEqual(code, 0)
        self.assertIn(GETTING_STARTED_GUIDE, out.getvalue())
        self.assertIn("python3 -m panopticon.sync", out.getvalue())

    def test_rerun_refreshes_instance_default_branch_in_existing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "panopticon" / "config.json"
            # Simulate a repo already initialized by finalization, without instance_default_branch
            # (e.g. the user's exact report: it couldn't be resolved the first time).
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({
                "schema_version": 1, "repo": "svc-a", "instance": "acme/instance",
                "workflow_ref": "v1", "docs_location": "docs",
            }))
            code = bootstrap_main(
                env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok",
                     "PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                child_root=tmp,
                urlopen=self._router(),
            )
            doc = json.loads(config_path.read_text())
        self.assertEqual(code, 0)
        self.assertEqual(doc["instance_default_branch"], "main")
        self.assertEqual(doc["repo"], "svc-a")  # other fields untouched

    def test_first_bootstrap_never_creates_config_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok",
                     "PANOPTICON_SKILLS_LOCATION": ".claude/skills"},
                child_root=tmp,
                urlopen=self._router(),
            )
            config_exists = (Path(tmp) / "panopticon" / "config.json").exists()
        self.assertEqual(code, 0)
        self.assertFalse(config_exists)


# ── Agent prompts ─────────────────────────────────────────────────────────────

class TestAgentPrompts(unittest.TestCase):
    def test_contains_single_slash_command(self):
        text = agent_prompts()
        self.assertIn("/panopticon-init", text)

    def test_only_one_prompt_is_printed(self):
        # Exactly one pasteable slash-command line — no separate prompts for the individual
        # steps panopticon-init now sequences internally.
        text = agent_prompts()
        self.assertNotIn("/panopticon-doc-generation", text)
        self.assertNotIn("/panopticon-interface-naming", text)
        self.assertNotIn("/panopticon-interface-extraction", text)
        self.assertNotIn("Prompt 1", text)
        self.assertNotIn("Prompt 2", text)
        self.assertNotIn("Prompt 3", text)

    def test_no_instance_slug_substitution(self):
        # panopticon-init self-discovers the instance slug from the wired caller workflow file,
        # so the prompt needs no per-instance interpolation and takes no argument.
        text = agent_prompts()
        self.assertNotIn("panopticon.init_repo --instance", text)

    def test_does_not_hardcode_agents_skills_as_sole_location(self):
        text = agent_prompts()
        self.assertNotIn("loads skills from .agents/skills/", text)

    def test_git_add_stages_everything_not_just_agents_skills(self):
        # The skills location is chosen at install time and can differ from .agents/skills/, so a
        # hardcoded `git add .agents/skills/` would silently skip whatever was actually created.
        text = agent_prompts()
        self.assertIn("git add -A", text)
        self.assertNotIn("git add .github/workflows/ .agents/skills/", text)


if __name__ == "__main__":
    unittest.main()
