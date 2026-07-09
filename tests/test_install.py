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
    SUPPORTED_TOOLS,
    agent_prompts,
    caller_workflow_text,
    check_prerequisites,
    download_skills,
    duplicate_skill_dir,
    manual_verification_steps,
    outlier_tools,
    reconcile_ides,
    resolve_instance,
    resolve_token,
    select_ides,
    select_reconcile_strategy,
    symlink_skill_dir,
    wire_workflows,
)
from panopticon.bootstrap import main as bootstrap_main


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

    def test_no_token_returns_manual_steps_without_calling_api(self):
        def urlopen(request, timeout=30):
            raise AssertionError("should not call the API when no token is available")
        report = check_prerequisites("acme", token=None, urlopen=urlopen)
        text = "\n".join(report)
        for name in (*ORG_SECRETS, *ORG_VARS):
            self.assertIn(name, text)
        self.assertIn("gh secret list --org acme", text)
        self.assertIn("gh variable list --org acme", text)
        self.assertIn("github.com/organizations/acme/settings/secrets/actions", text)

    def test_no_token_manual_steps_not_framed_as_error(self):
        report = manual_verification_steps("acme")
        text = "\n".join(report)
        self.assertNotIn("error", text.lower())
        self.assertNotIn("fail", text.lower())


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
                return BytesIO(json.dumps({"tree": []}).encode())
            if "actions/secrets" in url:
                return BytesIO(json.dumps({"secrets": [{"name": n} for n in secrets]}).encode())
            if "actions/variables" in url:
                return BytesIO(json.dumps({"variables": [{"name": n} for n in variables]}).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_no_org_config_wires_workflows_to_default_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok"},
                child_root=tmp,
                urlopen=self._router(org_config_content=None),
            )
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
        self.assertEqual(code, 0)
        self.assertIn("uses: acme/instance/.github/workflows/panopticon-pr.yml@main", text)

    def test_org_config_workflow_ref_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok"},
                child_root=tmp,
                urlopen=self._router(org_config_content=json.dumps({"workflow_ref": "v2"}).encode()),
            )
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
        self.assertEqual(code, 0)
        self.assertIn("uses: acme/instance/.github/workflows/panopticon-pr.yml@v2", text)


# ── IDE / tool compatibility ────────────────────────────────────────────────────

class TestOutlierTools(unittest.TestCase):
    def test_filters_to_non_compatible(self):
        self.assertEqual(outlier_tools(["vscode", "claude-code", "cursor"]), ["claude-code"])

    def test_unknown_tool_ignored(self):
        self.assertEqual(outlier_tools(["not-a-real-tool"]), [])


class TestSelectIdes(unittest.TestCase):
    def test_env_var_wins(self):
        result = select_ides(env={"PANOPTICON_IDES": "vscode, claude-code"})
        self.assertEqual(result, ["vscode", "claude-code"])

    def test_prompt_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = select_ides(env={}, prompt_fn=lambda _: "cursor,claude-code", child_root=tmp)
        self.assertEqual(result, ["cursor", "claude-code"])

    def test_blank_prompt_answer_means_no_extra_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = select_ides(env={}, prompt_fn=lambda _: "", child_root=tmp)
        self.assertEqual(result, [])

    def test_non_interactive_defaults_to_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.stdin.isatty", return_value=False):
                result = select_ides(env={}, child_root=tmp)
        self.assertEqual(result, [])

    def test_detects_already_reconciled_tool_without_prompting(self):
        def no_prompt(_):
            raise AssertionError("should not prompt when artifacts already exist")

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".claude" / "skills").mkdir(parents=True)
            result = select_ides(env={}, prompt_fn=no_prompt, child_root=tmp)
        self.assertEqual(result, ["claude-code"])


class TestSelectReconcileStrategy(unittest.TestCase):
    def test_env_var_duplicate(self):
        result = select_reconcile_strategy(["claude-code"], env={"PANOPTICON_IDE_RECONCILE": "duplicate"})
        self.assertEqual(result, ("duplicate", None))

    def test_env_var_symlink(self):
        result = select_reconcile_strategy(["claude-code"], env={"PANOPTICON_IDE_RECONCILE": "symlink"})
        self.assertEqual(result, ("symlink", None))

    def test_env_var_single(self):
        result = select_reconcile_strategy(
            ["claude-code", "x"], env={"PANOPTICON_IDE_RECONCILE": "single:claude-code"}
        )
        self.assertEqual(result, ("single", "claude-code"))

    def test_non_interactive_defaults_to_duplicate(self):
        with patch("sys.stdin.isatty", return_value=False):
            result = select_reconcile_strategy(["claude-code"], env={})
        self.assertEqual(result, ("duplicate", None))

    def test_prompt_single_with_one_outlier_skips_which_one_question(self):
        prompts = []

        def fake_prompt(msg):
            prompts.append(msg)
            return "single"

        result = select_reconcile_strategy(["claude-code"], env={}, prompt_fn=fake_prompt)
        self.assertEqual(result, ("single", "claude-code"))
        self.assertEqual(len(prompts), 1)


class TestDuplicateAndSymlinkSkillDir(unittest.TestCase):
    def test_duplicate_copies_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("hello")
            duplicate_skill_dir(".claude/skills", tmp)
            copied = Path(tmp) / ".claude" / "skills" / "panopticon-foo" / "SKILL.md"
            exists = copied.exists()
            content = copied.read_text() if exists else None
        self.assertTrue(exists)
        self.assertEqual(content, "hello")

    def test_duplicate_replaces_existing_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills").mkdir(parents=True)
            (Path(tmp) / ".claude").mkdir()
            (Path(tmp) / ".claude" / "skills").symlink_to(Path(tmp) / ".agents" / "skills")
            duplicate_skill_dir(".claude/skills", tmp)
            dest = Path(tmp) / ".claude" / "skills"
            is_symlink, is_dir = dest.is_symlink(), dest.is_dir()
        self.assertFalse(is_symlink)
        self.assertTrue(is_dir)

    def test_symlink_creates_link_to_agents_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills").mkdir(parents=True)
            ok = symlink_skill_dir(".claude/skills", tmp)
            is_symlink = (Path(tmp) / ".claude" / "skills").is_symlink()
        self.assertTrue(ok)
        self.assertTrue(is_symlink)

    def test_symlink_failure_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills").mkdir(parents=True)
            with patch("pathlib.Path.symlink_to", side_effect=OSError("no symlinks here")):
                ok = symlink_skill_dir(".claude/skills", tmp)
        self.assertFalse(ok)


class TestReconcileIdes(unittest.TestCase):
    def test_no_outliers_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = reconcile_ides(["vscode", "cursor"], env={}, child_root=tmp)
        self.assertEqual(lines, [])

    def test_duplicate_strategy_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills" / "panopticon-foo").mkdir(parents=True)
            lines = reconcile_ides(
                ["claude-code"], env={"PANOPTICON_IDE_RECONCILE": "duplicate"}, child_root=tmp
            )
            is_dir = (Path(tmp) / ".claude" / "skills" / "panopticon-foo").is_dir()
        self.assertTrue(is_dir)
        self.assertIn("duplicated skills into .claude/skills", "\n".join(lines))

    def test_symlink_strategy_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills").mkdir(parents=True)
            lines = reconcile_ides(
                ["claude-code"], env={"PANOPTICON_IDE_RECONCILE": "symlink"}, child_root=tmp
            )
            is_symlink = (Path(tmp) / ".claude" / "skills").is_symlink()
        self.assertTrue(is_symlink)

    def test_single_strategy_skips_other_outliers(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills").mkdir(parents=True)
            with patch.dict(SUPPORTED_TOOLS, {"fake-tool": ("Fake Tool", False, ".faketool/skills")}):
                lines = reconcile_ides(
                    ["claude-code", "fake-tool"],
                    env={"PANOPTICON_IDE_RECONCILE": "single:claude-code"},
                    child_root=tmp,
                )
                claude_exists = (Path(tmp) / ".claude" / "skills").exists()
                fake_exists = (Path(tmp) / ".faketool" / "skills").exists()
        self.assertTrue(claude_exists)
        self.assertFalse(fake_exists)
        self.assertIn("skipped Fake Tool", "\n".join(lines))

    def test_rerun_refreshes_existing_duplicate_without_reprompting(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills" / "panopticon-foo").mkdir(parents=True)
            (Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md").write_text("v1")
            duplicate_skill_dir(".claude/skills", tmp)
            # Simulate .agents/skills/ content changing between runs.
            (Path(tmp) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md").write_text("v2")

            def no_prompt(_):
                raise AssertionError("must not prompt on a re-run with existing artifacts")

            lines = reconcile_ides(["claude-code"], env={}, prompt_fn=no_prompt, child_root=tmp)
            refreshed = (Path(tmp) / ".claude" / "skills" / "panopticon-foo" / "SKILL.md").read_text()
        self.assertEqual(refreshed, "v2")
        self.assertIn("refreshed duplicated skills", "\n".join(lines))

    def test_rerun_leaves_existing_symlink_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".agents" / "skills").mkdir(parents=True)
            symlink_skill_dir(".claude/skills", tmp)

            def no_prompt(_):
                raise AssertionError("must not prompt on a re-run with an existing symlink")

            lines = reconcile_ides(["claude-code"], env={}, prompt_fn=no_prompt, child_root=tmp)
            is_symlink = (Path(tmp) / ".claude" / "skills").is_symlink()
        self.assertIn("already a symlink", "\n".join(lines))
        self.assertTrue(is_symlink)


class TestMainIdeReconciliation(unittest.TestCase):
    def _router(self):
        from urllib.error import HTTPError

        def urlopen(request, timeout=30):
            url = request.full_url
            if "contents/panopticon.config.json" in url:
                raise HTTPError(url, 404, "Not Found", {}, BytesIO(b"{}"))
            if "git/trees" in url:
                return BytesIO(json.dumps({"tree": []}).encode())
            if "actions/secrets" in url:
                return BytesIO(json.dumps({"secrets": [{"name": n} for n in ORG_SECRETS]}).encode())
            if "actions/variables" in url:
                return BytesIO(json.dumps({"variables": [{"name": n} for n in ORG_VARS]}).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_env_selection_and_reconcile_flow_through_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={
                    "PANOPTICON_INSTANCE": "acme/instance",
                    "GH_TOKEN": "tok",
                    "PANOPTICON_IDES": "claude-code",
                    "PANOPTICON_IDE_RECONCILE": "symlink",
                },
                child_root=tmp,
                urlopen=self._router(),
            )
            is_symlink = (Path(tmp) / ".claude" / "skills").is_symlink()
        self.assertEqual(code, 0)
        self.assertTrue(is_symlink)

    def test_no_ide_selection_creates_no_extra_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.stdin.isatty", return_value=False):
                code = bootstrap_main(
                    env={"PANOPTICON_INSTANCE": "acme/instance", "GH_TOKEN": "tok"},
                    child_root=tmp,
                    urlopen=self._router(),
                )
            claude_exists = (Path(tmp) / ".claude").exists()
        self.assertEqual(code, 0)
        self.assertFalse(claude_exists)


# ── Agent prompts ─────────────────────────────────────────────────────────────

class TestAgentPrompts(unittest.TestCase):
    def test_contains_all_skill_names(self):
        text = agent_prompts("acme/instance")
        self.assertIn("panopticon-doc-generation", text)
        self.assertIn("panopticon-interface-naming", text)
        self.assertIn("panopticon-interface-extraction", text)

    def test_prompts_use_slash_commands(self):
        text = agent_prompts("acme/instance")
        self.assertIn("/panopticon-doc-generation", text)
        self.assertIn("/panopticon-interface-naming", text)
        self.assertIn("/panopticon-interface-extraction", text)

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
