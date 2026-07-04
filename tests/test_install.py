"""Bootstrap installer: skill download, workflow wiring, env/prompt resolution, idempotency."""

import base64
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from panopticon.bootstrap import (
    CALLER_WORKFLOWS,
    ORG_SECRETS,
    ORG_VARS,
    agent_prompts,
    caller_workflow_text,
    check_prerequisites,
    download_skills,
    resolve_instance,
    resolve_token,
    wire_workflows,
)


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
        text = caller_workflow_text("panopticon-pr.yml", "acme/instance", "v1")
        self.assertIn("uses: acme/instance/.github/workflows/panopticon-pr.yml@v1", text)
        self.assertIn("secrets: inherit", text)
        self.assertNotIn("PANOPTICON_", text)

    def test_merge_workflow_uses_supplied_branch(self):
        text = caller_workflow_text("panopticon-merge.yml", "acme/instance", "v1", "trunk")
        self.assertIn("branches: [trunk]", text)

    def test_pr_close_workflow(self):
        text = caller_workflow_text("panopticon-pr-close.yml", "acme/instance", "v2")
        self.assertIn("types: [closed]", text)
        self.assertIn("@v2", text)


class TestWireWorkflows(unittest.TestCase):
    def test_creates_all_three_workflow_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            wire_workflows("acme/instance", "v1", tmp)
            names = {p.name for p in (Path(tmp) / ".github" / "workflows").iterdir()}
        self.assertEqual(names, set(CALLER_WORKFLOWS))

    def test_idempotent_rerun_updates_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            wire_workflows("acme/instance", "v1", tmp)
            wire_workflows("acme/instance", "v2", tmp)
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
            count = len(list((Path(tmp) / ".github" / "workflows").iterdir()))
        self.assertIn("@v2", text)
        self.assertEqual(count, len(CALLER_WORKFLOWS))

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            wire_workflows("acme/instance", "v1", tmp)
            self.assertTrue((Path(tmp) / ".github" / "workflows").is_dir())


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
        paths = [".agents/skills/my-skill/SKILL.md"]
        tree, urlopen = self._make_tree_and_urlopen(paths)
        with tempfile.TemporaryDirectory() as tmp:
            count = download_skills("acme", "instance", "main", tree, child_root=tmp,
                                    urlopen=urlopen)
            local = Path(tmp) / ".agents" / "skills" / "my-skill" / "SKILL.md"
            self.assertEqual(count, 1)
            self.assertTrue(local.exists())

    def test_skips_non_skill_tree_entries(self):
        tree = [
            _tree_entry(".agents/skills/foo/SKILL.md"),
            _tree_entry("panopticon/config.py"),
            _tree_entry(".github/workflows/pr.yml"),
        ]
        responses = [(".agents/skills/foo/SKILL.md", _file_response(b"# foo"))]
        urlopen = _make_urlopen(responses)
        with tempfile.TemporaryDirectory() as tmp:
            count = download_skills("acme", "instance", "main", tree, child_root=tmp,
                                    urlopen=urlopen)
        self.assertEqual(count, 1)

    def test_idempotent_rerun_overwrites_existing(self):
        path = ".agents/skills/foo/SKILL.md"
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
        report = check_prerequisites("acme", token="tok", urlopen=urlopen)
        self.assertEqual(report, [])

    def test_missing_secret_reported(self):
        urlopen = self._make_urlopen_for_prereqs(["PANOPTICON_LLM_API_KEY"], list(ORG_VARS))
        report = check_prerequisites("acme", token="tok", urlopen=urlopen)
        text = "\n".join(report)
        self.assertIn("PANOPTICON_INSTANCE_TOKEN", text)

    def test_missing_variable_reported(self):
        urlopen = self._make_urlopen_for_prereqs(list(ORG_SECRETS), ["PANOPTICON_LLM_MODEL"])
        report = check_prerequisites("acme", token="tok", urlopen=urlopen)
        text = "\n".join(report)
        self.assertIn("PANOPTICON_LLM_ENDPOINT", text)

    def test_api_failure_reported_non_blocking(self):
        def urlopen(request, timeout=30):
            from urllib.error import HTTPError
            raise HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(b"denied"))
        report = check_prerequisites("acme", token="tok", urlopen=urlopen)
        self.assertTrue(len(report) > 0)
        self.assertIn("could not verify", "\n".join(report))


# ── Agent prompts ─────────────────────────────────────────────────────────────

class TestAgentPrompts(unittest.TestCase):
    def test_contains_all_skill_names(self):
        text = agent_prompts("acme/instance")
        self.assertIn("panopticon-doc-generation", text)
        self.assertIn("panopticon-interface-naming", text)
        self.assertIn("panopticon-interface-extraction", text)

    def test_finalize_command_is_copy_pasteable(self):
        text = agent_prompts("acme/instance")
        self.assertIn("python3 -m panopticon.init_repo --instance acme/instance", text)

    def test_instance_slug_interpolated(self):
        text = agent_prompts("myorg/myinstance")
        self.assertIn("myorg/myinstance", text)

    def test_three_distinct_prompts_present(self):
        text = agent_prompts("acme/instance")
        self.assertIn("Prompt 1", text)
        self.assertIn("Prompt 2", text)
        self.assertIn("Prompt 3", text)


if __name__ == "__main__":
    unittest.main()
