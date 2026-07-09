"""Bootstrap installer: skill download, workflow wiring, env/prompt resolution, idempotency."""

import base64
import json
import os
import pty
import tempfile
import threading
import time
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from panopticon.bootstrap import (
    CALLER_WORKFLOWS,
    DEFAULT_SKILLS_LOCATION,
    LOCAL_TOOLING_MODULES,
    ORG_SECRETS,
    ORG_VARS,
    TOOL_LOCATIONS,
    _apply_key,
    _arrow_key_menu,
    _detect_existing_location,
    _resolve_typed_answer,
    agent_prompts,
    caller_workflow_text,
    candidate_locations,
    check_prerequisites,
    download_local_tooling,
    download_skills,
    manual_verification_steps,
    resolve_instance,
    resolve_token,
    select_skills_location,
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
            for name in LOCAL_TOOLING_MODULES:
                if f"/contents/panopticon/{name}" in url:
                    return BytesIO(json.dumps(_file_response(f"# {name}".encode())).encode())
            if "actions/secrets" in url:
                return BytesIO(json.dumps({"secrets": [{"name": n} for n in secrets]}).encode())
            if "actions/variables" in url:
                return BytesIO(json.dumps({"variables": [{"name": n} for n in variables]}).encode())
            raise AssertionError(f"unexpected url: {url}")

        return urlopen

    def test_no_org_config_wires_workflows_to_default_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={
                    "PANOPTICON_INSTANCE": "acme/instance",
                    "GH_TOKEN": "tok",
                    "PANOPTICON_SKILLS_LOCATION": ".agents/skills",
                },
                child_root=tmp,
                urlopen=self._router(org_config_content=None),
            )
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
        self.assertEqual(code, 0)
        self.assertIn("uses: acme/instance/.github/workflows/panopticon-pr.yml@main", text)

    def test_org_config_workflow_ref_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = bootstrap_main(
                env={
                    "PANOPTICON_INSTANCE": "acme/instance",
                    "GH_TOKEN": "tok",
                    "PANOPTICON_SKILLS_LOCATION": ".agents/skills",
                },
                child_root=tmp,
                urlopen=self._router(org_config_content=json.dumps({"workflow_ref": "v2"}).encode()),
            )
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
        self.assertEqual(code, 0)
        self.assertIn("uses: acme/instance/.github/workflows/panopticon-pr.yml@v2", text)


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
                raise HTTPError(url, 404, "Not Found", {}, BytesIO(b"{}"))
            if "git/trees" in url:
                return BytesIO(json.dumps({"tree": [_tree_entry(skill_path)]}).encode())
            if "contents/" + skill_path in url:
                return BytesIO(json.dumps(_file_response(b"# panopticon-foo")).encode())
            for name in LOCAL_TOOLING_MODULES:
                if f"/contents/panopticon/{name}" in url:
                    return BytesIO(json.dumps(_file_response(f"# {name}".encode())).encode())
            if "actions/secrets" in url:
                return BytesIO(json.dumps({"secrets": [{"name": n} for n in ORG_SECRETS]}).encode())
            if "actions/variables" in url:
                return BytesIO(json.dumps({"variables": [{"name": n} for n in ORG_VARS]}).encode())
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
        self.assertEqual(vendored, set(LOCAL_TOOLING_MODULES))

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
