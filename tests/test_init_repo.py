"""Init tooling: validation gate, workflow wiring, docs-location adoption, idempotent re-init."""

import unittest
import tempfile
from pathlib import Path

from panopticon.config import load_repo_config
from panopticon.index import save_index
from panopticon.init_repo import (
    CALLER_WORKFLOWS,
    detect_docs_location,
    initialize,
    verify_org_secrets,
)

from .helpers import load_fixture
from .test_docs import make_docs_tree


def make_valid_child(root, repo="svc-a", docs="docs"):
    root = Path(root)
    make_docs_tree(root / docs)
    doc = load_fixture("local_svc_a.json")
    save_index(doc, root / "panopticon" / "index.json", repo=repo)
    from panopticon.docs import write_interface_docs

    write_interface_docs(doc, root / docs, repo)


def run_init(tmp, **overrides):
    kwargs = {
        "child_root": tmp,
        "repo_name": "svc-a",
        "instance": "acme/panopticon-instance",
        "workflow_ref": "v1",
        "docs_location": None,
        "skip_secret_check": True,
        "prompt": lambda _: "",
    }
    kwargs.update(overrides)
    return initialize(**kwargs)


class TestValidationGate(unittest.TestCase):
    def test_no_config_written_when_docs_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, messages = run_init(tmp, docs_location="docs")
            self.assertEqual(code, 1)
            self.assertIsNone(load_repo_config(tmp))
            self.assertFalse((Path(tmp) / ".github").exists())
        text = "\n".join(messages)
        self.assertIn("NOT written", text)
        self.assertIn("architecture overview", text)
        self.assertIn("local index", text)

    def test_successful_init_writes_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            code, messages = run_init(tmp)
            self.assertEqual(code, 0, messages)
            config = load_repo_config(tmp)
            workflows = sorted(p.name for p in (Path(tmp) / ".github" / "workflows").iterdir())
        self.assertEqual(config["repo"], "svc-a")
        self.assertEqual(config["docs_location"], "docs")
        self.assertEqual(workflows, sorted(CALLER_WORKFLOWS))

    def test_caller_workflows_reference_instance_at_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            run_init(tmp, workflow_ref="v2.1")
            text = (Path(tmp) / ".github" / "workflows" / "panopticon-pr.yml").read_text()
        self.assertIn(
            "uses: acme/panopticon-instance/.github/workflows/panopticon-pr.yml@v2.1", text
        )
        self.assertIn("secrets: inherit", text)
        self.assertNotIn("PANOPTICON_", text)  # no per-repo secret configuration


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


class TestIdempotentReinit(unittest.TestCase):
    def test_reinit_updates_in_place_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            self.assertEqual(run_init(tmp)[0], 0)
            code, messages = run_init(tmp, workflow_ref="v2")
            self.assertEqual(code, 0)
            workflows_dir = Path(tmp) / ".github" / "workflows"
            self.assertEqual(len(list(workflows_dir.iterdir())), len(CALLER_WORKFLOWS))
            self.assertIn("@v2", (workflows_dir / "panopticon-pr.yml").read_text())
            config = load_repo_config(tmp)
        self.assertEqual(config["workflow_ref"], "v2")
        self.assertIn("idempotent re-init", "\n".join(messages))


class TestSecretVerification(unittest.TestCase):
    def gh_stub(self, returncode=0, stdout="", stderr=""):
        class Result:
            pass

        result = Result()
        result.returncode, result.stdout, result.stderr = returncode, stdout, stderr
        return lambda *args, **kwargs: result

    def test_missing_secret_reported_with_instructions(self):
        report = verify_org_secrets(
            "acme", runner=self.gh_stub(stdout="PANOPTICON_LLM_API_KEY\nPANOPTICON_LLM_ENDPOINT\n")
        )
        text = "\n".join(report)
        self.assertIn("PANOPTICON_INSTANCE_TOKEN", text)
        self.assertIn("settings/secrets/actions", text)

    def test_all_present(self):
        report = verify_org_secrets(
            "acme",
            runner=self.gh_stub(
                stdout="PANOPTICON_LLM_API_KEY\nPANOPTICON_LLM_ENDPOINT\nPANOPTICON_INSTANCE_TOKEN\n"
            ),
        )
        self.assertIn("all org-level secrets present", report[0])

    def test_gh_failure_is_report_only(self):
        report = verify_org_secrets("acme", runner=self.gh_stub(returncode=1, stderr="HTTP 403"))
        self.assertIn("could not verify", report[0])

    def test_missing_secrets_never_block_init(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            make_valid_child(tmp)
            with mock.patch(
                "panopticon.init_repo.verify_org_secrets",
                return_value=["missing org-level secret PANOPTICON_INSTANCE_TOKEN: ..."],
            ):
                code, messages = run_init(tmp, skip_secret_check=False)
        # verification reported a missing secret, but init still completed
        self.assertEqual(code, 0, messages)
        self.assertIn("missing org-level secret", "\n".join(messages))


if __name__ == "__main__":
    unittest.main()
