"""Structural parity and isolation checks for configurable provider workflows."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
CONFIGURATION_ACTION = ROOT / ".github" / "actions" / "configure-panopticon" / "action.yml"
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
        for provider in ("litellm", "bedrock"):
            self.assertIn(f"configure-panopticon-{provider}.yml", text)
            self.assertIn(f"gh workflow run configure-panopticon-{provider}.yml", text)
        self.assertIn("| ", text)
        self.assertIn("PANOPTICON_INSTANCE='", text)
        self.assertIn('child_config.get("instance_default_branch") or "main"', text)
        self.assertNotIn("GITHUB_REF_NAME", text)
        self.assertNotIn("export PANOPTICON_INSTANCE", text)
        self.assertNotIn("select-a-provider", text)

    def test_provider_configuration_workflows_are_fixed_and_isolated(self):
        common_inputs = (
            "instance_token_name:",
            "model_variable_name:",
            "timeout_seconds_variable_name:",
            "max_attempts_variable_name:",
            "max_correction_attempts_variable_name:",
            "job_timeout_minutes_variable_name:",
        )
        expected_provider_inputs = {
            "litellm": ("api_key_name:", "endpoint_variable_name:"),
            "bedrock": (
                "credential_mode:",
                "aws_region_variable_name:",
                "aws_role_arn_variable_name:",
            ),
        }
        excluded_provider_inputs = {
            "litellm": expected_provider_inputs["bedrock"],
            "bedrock": expected_provider_inputs["litellm"],
        }
        for provider in ("litellm", "bedrock"):
            text = self.workflow(f"configure-panopticon-{provider}.yml")
            self.assertIn(f"provider: {provider}", text)
            self.assertNotIn("provider:\n", text.split("inputs:", 1)[1].split("permissions:", 1)[0])
            self.assertIn("contents: write", text)
            self.assertIn("uses: ./.github/actions/configure-panopticon", text)
            self.assertIn("group: panopticon-provider-configuration-${{ github.ref }}", text)
            for input_name in common_inputs + expected_provider_inputs[provider]:
                with self.subTest(provider=provider, input_name=input_name):
                    self.assertIn(input_name, text)
            for input_name in excluded_provider_inputs[provider]:
                with self.subTest(provider=provider, excluded=input_name):
                    self.assertNotIn(input_name, text)
            self.assertNotIn("select-a-provider", text)
            self.assertNotIn("secret_value", text)
            self.assertNotIn("api_key_value", text)

    def test_configuration_action_preserves_shared_behavior(self):
        text = CONFIGURATION_ACTION.read_text(encoding="utf-8")
        self.assertIn("PYTHONPATH: ${{ github.workspace }}", text)
        self.assertIn("from panopticon.configure_instance import configure", text)
        self.assertIn("Panopticon provider configuration is invalid", text)
        self.assertIn("GITHUB_STEP_SUMMARY", text)
        self.assertIn("No credential values were accepted or persisted", text)
        self.assertIn("git diff --quiet -- panopticon.config.json", text)
        self.assertIn("Configuration already matches", text)
        self.assertIn("could not be pushed", text)
        self.assertIn("git show --format= -- panopticon.config.json", text)
        self.assertIn("exit 1", text)

    def test_workflow_failure_paths_write_actionable_summaries(self):
        expected_summary_text = {
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
        configuration_action = CONFIGURATION_ACTION.read_text(encoding="utf-8")
        self.assertIn("Panopticon provider configuration is invalid", configuration_action)
        self.assertIn("GITHUB_STEP_SUMMARY", configuration_action)
        self.assertIn("see the step summary", configuration_action)

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
