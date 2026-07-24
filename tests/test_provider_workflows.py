"""Structural parity and isolation checks for configurable provider workflows."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
COMMON_PR_PHASES = (
    "Initialization check",
    "Validate provider inputs",
    "Validate provider configuration revision",
    "Provider preflight",
    "Tooling-currency check (advisory only)",
    "Doc-drift check",
    "Index-currency check",
    "Diagram-existence check",
    "Pre-merge simulation",
    "Post combined report",
    "Push branch state to instance repo",
    "Apply gating",
)


class TestProviderWorkflows(unittest.TestCase):
    def workflow(self, name):
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def test_separate_provider_entrypoints_preserve_common_phases(self):
        for provider in ("litellm", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            for phase in COMMON_PR_PHASES:
                with self.subTest(provider=provider, phase=phase):
                    self.assertEqual(text.count(f"- name: {phase}"), 1)
            self.assertIn("configuration_revision:", text)
            self.assertIn("configuration_names:", text)
            self.assertIn("timeout-minutes:", text)
            self.assertIn("Post combined report", text)
            self.assertIn("Apply gating", text)
            self.assertNotIn("secrets: inherit", text)

    def test_litellm_workflow_has_no_bedrock_setup(self):
        text = self.workflow("panopticon-pr-litellm.yml")
        self.assertIn("PANOPTICON_LLM_PROVIDER: litellm", text)
        self.assertNotIn("configure-aws-credentials", text)
        self.assertNotIn("requirements-bedrock.txt", text)
        self.assertNotIn("id-token: write", text)

    def test_bedrock_workflow_supports_trusted_credential_modes_and_pinned_dependency(self):
        text = self.workflow("panopticon-pr-bedrock.yml")
        self.assertIn("PANOPTICON_LLM_PROVIDER: bedrock", text)
        self.assertIn("id-token: write", text)
        self.assertIn("aws-actions/configure-aws-credentials@v6.1.2", text)
        self.assertIn("credential_mode:", text)
        self.assertIn("inputs.credential_mode == 'github-oidc'", text)
        self.assertIn("inputs.credential_mode == 'instance-managed'", text)
        self.assertIn(".github/actions/panopticon-aws-credentials/action.yml", text)
        self.assertIn("actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1", text)
        self.assertIn("pip install --upgrade -r", text)
        self.assertIn("requirements-bedrock.txt", text)

    def test_legacy_guard_prints_configuration_and_exact_bootstrap_commands(self):
        text = self.workflow("panopticon-pr.yml")
        self.assertNotIn("panopticon.drift", text)
        self.assertIn("actions/workflows/configure-panopticon.yml", text)
        self.assertIn("gh workflow run configure-panopticon.yml", text)
        self.assertIn("| ", text)
        self.assertIn("PANOPTICON_INSTANCE='", text)
        self.assertIn('child_config.get("instance_default_branch") or "main"', text)
        self.assertNotIn("GITHUB_REF_NAME", text)
        self.assertNotIn("export PANOPTICON_INSTANCE", text)

    def test_configuration_workflow_uses_clear_optional_name_inputs(self):
        text = self.workflow("configure-panopticon.yml")
        self.assertIn("default: select-a-provider", text)
        self.assertIn("- bedrock", text)
        self.assertIn("- litellm", text)
        self.assertIn("instance_token_name:", text)
        self.assertIn("GitHub token that checks out the private instance repo", text)
        self.assertIn("e.g. value gpt-4o-mini for LiteLLM", text)
        self.assertIn("Bedrock AWS region variable name", text)
        self.assertIn("Bedrock IAM role ARN variable name", text)
        self.assertIn("instance-managed uses the fixed instance action", text)
        for input_name in (
            "timeout_seconds_variable_name:",
            "max_attempts_variable_name:",
            "max_correction_attempts_variable_name:",
            "job_timeout_minutes_variable_name:",
        ):
            with self.subTest(input_name=input_name):
                self.assertIn(input_name, text)
        self.assertNotIn("budget_variable_names", text)
        self.assertNotIn("json.loads", text)
        self.assertNotIn("secret_value", text)
        self.assertNotIn("api_key_value", text)

    def test_configuration_workflow_reports_noop_and_push_failure(self):
        text = self.workflow("configure-panopticon.yml")
        self.assertIn("PYTHONPATH: ${{ github.workspace }}", text)
        self.assertIn("git diff --quiet -- panopticon.config.json", text)
        self.assertIn("Configuration already matches", text)
        self.assertIn("could not be pushed", text)
        self.assertIn("git show --format= -- panopticon.config.json", text)
        self.assertIn("exit 1", text)

    def test_workflow_failure_paths_write_actionable_summaries(self):
        expected_summary_text = {
            "configure-panopticon.yml": "Panopticon provider configuration is invalid",
            "panopticon-pr-close.yml": "Panopticon instance branch cleanup failed",
            "panopticon-merge.yml": "Panopticon merge sync failed",
            "panopticon-pr-bedrock.yml": "Unsupported Bedrock credential mode",
            "panopticon-pr-litellm.yml": "Panopticon branch-state push failed",
        }
        for name, reason in expected_summary_text.items():
            with self.subTest(workflow=name):
                text = self.workflow(name)
                self.assertIn(reason, text)
                self.assertIn("GITHUB_STEP_SUMMARY", text)
                self.assertIn("see the step summary", text)

    def test_merge_and_close_accept_only_canonical_instance_token(self):
        for name in ("panopticon-merge.yml", "panopticon-pr-close.yml"):
            text = self.workflow(name)
            self.assertIn("instance_token:", text)
            self.assertIn("secrets.instance_token", text)
            self.assertNotIn("secrets.PANOPTICON_INSTANCE_TOKEN", text)
            self.assertIn(
                "PANOPTICON_INSTANCE='$instance' python3"
                if name == "panopticon-pr-close.yml"
                else "PANOPTICON_INSTANCE='$PANOPTICON_INSTANCE' python3",
                text,
            )
            self.assertIn("Review and commit the generated changes, push them", text)

    def test_stale_provider_revision_reports_exact_child_recovery(self):
        for provider in ("litellm", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            self.assertIn("provider configuration revision changed", text)
            self.assertIn("from panopticon.recovery import stale_caller_recovery", text)
            self.assertIn("from panopticon.recovery import missing_provider_recovery", text)
            self.assertIn("except ModuleNotFoundError", text)

    def test_legacy_guard_retains_a_self_contained_recovery_fallback(self):
        text = self.workflow("panopticon-pr.yml")
        self.assertNotIn("panopticon.recovery", text)
        self.assertIn("PANOPTICON_INSTANCE='{instance}' python3", text)


if __name__ == "__main__":
    unittest.main()
