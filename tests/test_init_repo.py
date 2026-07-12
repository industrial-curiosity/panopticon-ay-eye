"""Finalization step: validation gate, docs-location adoption, idempotent re-init."""

import json
import subprocess
import unittest
import unittest.mock
import tempfile
from pathlib import Path

from panopticon.config import load_repo_config
from panopticon.index import save_index
from panopticon.init_repo import (
    detect_docs_location,
    discover_workflow_ref,
    initialize,
    verify_org_secrets,
    _fallback_workflow_ref,
    _resolve_instance_default_branch,
)

from .helpers import load_fixture
from .test_docs import make_docs_tree


def write_caller_workflow(root, ref, instance="acme/panopticon-instance"):
    workflows_dir = Path(root) / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    (workflows_dir / "panopticon-pr.yml").write_text(
        "name: Panopticon PR checks\n"
        "on:\n  pull_request:\n"
        "jobs:\n"
        "  panopticon:\n"
        f"    uses: {instance}/.github/workflows/panopticon-pr.yml@{ref}\n"
        "    secrets: inherit\n"
    )


def make_valid_child(root, repo="svc-a", docs="docs"):
    root = Path(root)
    make_docs_tree(root / docs)
    doc = load_fixture("local_svc_a.json")
    save_index(doc, root / "panopticon" / "index.json", repo=repo)
    from panopticon.docs import write_interface_docs

    write_interface_docs(doc, root / docs, repo)


def _stub_runner(returncode=0, stdout="main\n", stderr=""):
    """A fake subprocess runner for `gh api`/`gh auth token` calls (used by `verify_org_secrets` and
    as a `gh auth token` fallback in token resolution) — never hits the network."""
    class Result:
        def __init__(self):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def runner(args, **kwargs):
        return Result()

    return runner


def _make_repo_metadata_urlopen(default_branch="main", fail=False):
    """Stub urlopen for the `GET /repos/{instance}` metadata call
    `_fetch_default_branch`/`_resolve_instance_default_branch` make."""
    from io import BytesIO
    from urllib.error import HTTPError

    def urlopen(request, timeout=30):
        if fail:
            raise HTTPError(request.full_url, 404, "Not Found", {}, BytesIO(b"{}"))
        return BytesIO(json.dumps({"default_branch": default_branch}).encode())

    return urlopen


def run_init(tmp, **overrides):
    kwargs = {
        "child_root": tmp,
        "repo_name": "svc-a",
        "instance": "acme/panopticon-instance",
        "workflow_ref": "v1",
        "docs_location": None,
        "skip_secret_check": True,
        "prompt": lambda _: "",
        "runner": _stub_runner(),
        # Hermetic default for instance_default_branch resolution: no ambient token, and a stub
        # urlopen that never hits the network — tests that don't care about this field simply get
        # it omitted (fail=True), same as any environment with no working GitHub auth.
        "env": {},
        "urlopen": _make_repo_metadata_urlopen(fail=True),
    }
    kwargs.update(overrides)
    return initialize(**kwargs)


class TestValidationGate(unittest.TestCase):
    def test_no_config_written_when_docs_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, messages = run_init(tmp, docs_location="docs")
            self.assertEqual(code, 1)
            self.assertIsNone(load_repo_config(tmp))
        text = "\n".join(messages)
        self.assertIn("NOT written", text)
        self.assertIn("architecture overview", text)
        self.assertIn("local index", text)

    def test_successful_finalization_writes_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            code, messages = run_init(tmp)
            self.assertEqual(code, 0, messages)
            config = load_repo_config(tmp)
        self.assertEqual(config["repo"], "svc-a")
        self.assertEqual(config["docs_location"], "docs")
        self.assertIn("wrote panopticon/config.json", "\n".join(messages))

    def test_config_is_last_artifact_written(self):
        """panopticon/config.json must not exist before validation passes."""
        with tempfile.TemporaryDirectory() as tmp:
            # Incomplete child — finalization fails; config must not be created.
            run_init(tmp, docs_location="docs")
            self.assertFalse((Path(tmp) / "panopticon" / "config.json").exists())
            # Complete child — finalization succeeds; config is now written.
            make_valid_child(tmp)
            code, _ = run_init(tmp)
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "panopticon" / "config.json").exists())


class TestDocsLocationAdoption(unittest.TestCase):
    def test_existing_docs_dir_is_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "documentation").mkdir()
            (Path(tmp) / "documentation" / "old.md").write_text("# old\n")
            location = detect_docs_location(tmp, prompt=lambda _: self.fail("must not prompt"))
        self.assertEqual(location, "documentation")

    def test_prompt_default_is_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_docs_location(tmp, prompt=lambda _: ""), "docs")
            self.assertEqual(detect_docs_location(tmp, prompt=lambda _: "handbook"), "handbook")

    def test_configured_location_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            location = detect_docs_location(tmp, configured="site", prompt=lambda _: self.fail("no prompt"))
        self.assertEqual(location, "site")


class TestIdempotentRefinalization(unittest.TestCase):
    def test_refinalization_updates_config_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            self.assertEqual(run_init(tmp, workflow_ref="v1")[0], 0)
            code, messages = run_init(tmp, workflow_ref="v2")
            self.assertEqual(code, 0)
            config = load_repo_config(tmp)
        self.assertEqual(config["workflow_ref"], "v2")
        self.assertIn("idempotent re-init", "\n".join(messages))


class TestDiscoverWorkflowRef(unittest.TestCase):
    def test_parses_ref_from_caller_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_caller_workflow(tmp, ref="main")
            self.assertEqual(discover_workflow_ref(tmp), "main")

    def test_parses_pinned_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_caller_workflow(tmp, ref="v2")
            self.assertEqual(discover_workflow_ref(tmp), "v2")

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(discover_workflow_ref(tmp))

    def test_unparseable_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflows_dir = Path(tmp) / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)
            (workflows_dir / "panopticon-pr.yml").write_text("name: not a caller workflow\n")
            self.assertIsNone(discover_workflow_ref(tmp))


class TestFallbackWorkflowRef(unittest.TestCase):
    def test_uses_child_repo_checked_out_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", "-b", "feature-x", tmp], check=True)
            subprocess.run(["git", "-C", tmp, "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", tmp, "config", "user.name", "Test"], check=True)
            (Path(tmp) / "README.md").write_text("x\n")
            subprocess.run(["git", "-C", tmp, "add", "README.md"], check=True)
            subprocess.run(["git", "-C", tmp, "commit", "-q", "-m", "init"], check=True)
            self.assertEqual(_fallback_workflow_ref(tmp), "feature-x")

    def test_falls_back_to_main_when_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_fallback_workflow_ref(tmp), "main")


class TestWorkflowRefDefaultsToDiscovery(unittest.TestCase):
    def test_no_explicit_ref_derives_from_wired_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            write_caller_workflow(tmp, ref="main")
            code, _ = run_init(tmp, workflow_ref=None)
            self.assertEqual(code, 0)
            config = load_repo_config(tmp)
        self.assertEqual(config["workflow_ref"], "main")

    def test_no_explicit_ref_derives_pinned_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            write_caller_workflow(tmp, ref="v2")
            code, _ = run_init(tmp, workflow_ref=None)
            self.assertEqual(code, 0)
            config = load_repo_config(tmp)
        self.assertEqual(config["workflow_ref"], "v2")

    def test_no_wired_workflow_falls_back_without_hardcoded_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            code, _ = run_init(tmp, workflow_ref=None)
            self.assertEqual(code, 0)
            config = load_repo_config(tmp)
        # Not a git repo (no .github/workflows/panopticon-pr.yml, no git init) — falls back to
        # "main" rather than silently implying a pinned tag like "v1" exists.
        self.assertEqual(config["workflow_ref"], "main")


class TestSecretVerification(unittest.TestCase):
    def gh_stub(self, returncode=0, stdout="", stderr=""):
        class Result:
            pass

        result = Result()
        result.returncode, result.stdout, result.stderr = returncode, stdout, stderr
        return lambda *args, **kwargs: result

    def gh_stub_url_aware(self, secrets_stdout="", vars_stdout="", returncode=0):
        """Return different output for secrets vs variables API calls."""
        class Result:
            pass

        def runner(*args, **kwargs):
            r = Result()
            r.returncode = returncode
            r.stderr = ""
            url = args[0][2]
            r.stdout = secrets_stdout if "secrets" in url else vars_stdout
            return r

        return runner

    def test_missing_secret_reported_with_instructions(self):
        report = verify_org_secrets(
            "acme",
            runner=self.gh_stub_url_aware(
                secrets_stdout="PANOPTICON_LLM_API_KEY\n",
                vars_stdout="PANOPTICON_LLM_ENDPOINT\nPANOPTICON_LLM_MODEL\n",
            ),
        )
        text = "\n".join(report)
        self.assertIn("PANOPTICON_INSTANCE_TOKEN", text)
        self.assertIn("settings/secrets/actions", text)

    def test_missing_variable_reported_with_instructions(self):
        report = verify_org_secrets(
            "acme",
            runner=self.gh_stub_url_aware(
                secrets_stdout="PANOPTICON_LLM_API_KEY\nPANOPTICON_INSTANCE_TOKEN\n",
                vars_stdout="PANOPTICON_LLM_MODEL\n",
            ),
        )
        text = "\n".join(report)
        self.assertIn("PANOPTICON_LLM_ENDPOINT", text)
        self.assertIn("settings/secrets/actions", text)

    def test_all_present(self):
        report = verify_org_secrets(
            "acme",
            runner=self.gh_stub_url_aware(
                secrets_stdout="PANOPTICON_LLM_API_KEY\nPANOPTICON_INSTANCE_TOKEN\n",
                vars_stdout="PANOPTICON_LLM_ENDPOINT\nPANOPTICON_LLM_MODEL\n",
            ),
        )
        self.assertIn("all org-level secrets present", report[0])

    def test_gh_failure_is_report_only(self):
        report = verify_org_secrets("acme", runner=self.gh_stub(returncode=1, stderr="HTTP 403"))
        text = "\n".join(report)
        for name in ("PANOPTICON_LLM_API_KEY", "PANOPTICON_INSTANCE_TOKEN",
                     "PANOPTICON_LLM_ENDPOINT", "PANOPTICON_LLM_MODEL"):
            self.assertIn(name, text)
        self.assertIn("gh secret list --org acme", text)
        self.assertIn("gh variable list --org acme", text)
        self.assertIn("settings/secrets/actions", text)

    def test_gh_not_installed_reports_manual_steps(self):
        with unittest.mock.patch("shutil.which", return_value=None):
            report = verify_org_secrets("acme", runner=self.gh_stub())
        text = "\n".join(report)
        self.assertIn("gh secret list --org acme", text)
        self.assertIn("settings/secrets/actions", text)

    def test_missing_secrets_never_block_finalization(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            with mock.patch(
                "panopticon.init_repo.verify_org_secrets",
                return_value=["missing org-level secret PANOPTICON_INSTANCE_TOKEN: ..."],
            ):
                code, messages = run_init(tmp, skip_secret_check=False)
        self.assertEqual(code, 0, messages)
        self.assertIn("missing org-level secret", "\n".join(messages))


class TestResolveInstanceDefaultBranch(unittest.TestCase):
    def test_resolves_via_gh_token_env_var(self):
        branch = _resolve_instance_default_branch(
            "acme/panopticon-instance", env={"GH_TOKEN": "tok"},
            urlopen=_make_repo_metadata_urlopen("main"),
        )
        self.assertEqual(branch, "main")

    def test_resolves_via_github_token_env_var(self):
        branch = _resolve_instance_default_branch(
            "acme/panopticon-instance", env={"GITHUB_TOKEN": "tok"},
            urlopen=_make_repo_metadata_urlopen("main"),
        )
        self.assertEqual(branch, "main")

    def test_non_main_branch_name_returned_as_is(self):
        branch = _resolve_instance_default_branch(
            "acme/panopticon-instance", env={"GH_TOKEN": "tok"},
            urlopen=_make_repo_metadata_urlopen("trunk"),
        )
        self.assertEqual(branch, "trunk")

    def test_works_with_env_token_even_when_gh_auth_login_was_never_run(self):
        """Regression test: the original implementation shelled out to `gh api`, which depends on
        `gh auth login` having been run interactively — a different, narrower precondition than
        GH_TOKEN/GITHUB_TOKEN, which bootstrap.py's own downloads already rely on successfully. A
        user can have a working GH_TOKEN and an installed-but-never-`gh auth login`-ed `gh` CLI at
        the same time; resolution must succeed via the token, never depending on `gh`'s own
        credential store."""
        with unittest.mock.patch("shutil.which", return_value="/usr/bin/gh"):
            branch = _resolve_instance_default_branch(
                "acme/panopticon-instance", env={"GH_TOKEN": "tok"},
                urlopen=_make_repo_metadata_urlopen("main"),
            )
        self.assertEqual(branch, "main")

    def test_api_failure_returns_none(self):
        branch = _resolve_instance_default_branch(
            "acme/panopticon-instance", env={"GH_TOKEN": "tok"},
            urlopen=_make_repo_metadata_urlopen(fail=True),
        )
        self.assertIsNone(branch)

    def test_no_token_still_attempts_unauthenticated_call(self):
        with unittest.mock.patch("shutil.which", return_value=None):
            branch = _resolve_instance_default_branch(
                "acme/panopticon-instance", env={},
                urlopen=_make_repo_metadata_urlopen("main"),
            )
        self.assertEqual(branch, "main")


class TestInitializeWritesInstanceDefaultBranch(unittest.TestCase):
    def test_resolved_branch_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            code, messages = run_init(
                tmp, env={"GH_TOKEN": "tok"}, urlopen=_make_repo_metadata_urlopen("main")
            )
            self.assertEqual(code, 0, messages)
            config = load_repo_config(tmp)
        self.assertEqual(config["instance_default_branch"], "main")

    def test_unresolvable_branch_is_omitted_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            code, messages = run_init(
                tmp, env={}, urlopen=_make_repo_metadata_urlopen(fail=True)
            )
            self.assertEqual(code, 0, messages)
            config = load_repo_config(tmp)
        self.assertNotIn("instance_default_branch", config)
        self.assertIn("could not resolve instance_default_branch", "\n".join(messages))

    def test_never_conflated_with_workflow_ref(self):
        """workflow_ref may be a pinned tag; instance_default_branch is resolved independently and
        must never be derived from it."""
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            code, messages = run_init(
                tmp, workflow_ref="v2", env={"GH_TOKEN": "tok"},
                urlopen=_make_repo_metadata_urlopen("main"),
            )
            self.assertEqual(code, 0, messages)
            config = load_repo_config(tmp)
        self.assertEqual(config["workflow_ref"], "v2")
        self.assertEqual(config["instance_default_branch"], "main")


if __name__ == "__main__":
    unittest.main()
