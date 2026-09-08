"""Structural parity and isolation checks for configurable provider workflows."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
CONFIGURATION_ACTION = ROOT / ".github" / "actions" / "configure-panopticon" / "action.yml"
DEFAULTS_ACTION = (
    ROOT / ".github" / "actions" / "panopticon-provider-defaults" / "action.yml"
)
COMMON_PR_PHASES = (
    "Initialization check",
    "Validate provider inputs",
    "Validate instance provider defaults action",
    "Resolve instance provider defaults",
    "Resolve effective provider values",
    "Validate provider configuration revision",
    "Run enabled feature checks",
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
REQUEST_BUDGET_DEFAULTS = {
    "timeout_seconds": "90",
    "max_attempts": "2",
    "max_correction_attempts": "2",
}


class TestProviderWorkflows(unittest.TestCase):
    def workflow(self, name):
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def test_separate_provider_entrypoints_preserve_common_phases(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            for phase in COMMON_PR_PHASES:
                with self.subTest(provider=provider, phase=phase):
                    self.assertEqual(text.count(f"- name: {phase}"), 1)
            self.assertIn("configuration_revision:", text)
            self.assertIn("configuration_names:", text)
            self.assertIn("timeout-minutes:", text)
            self.assertIn("configuration_defaults:", text)
            self.assertIn('default: "{}"', text)
            self.assertIn("Post combined report", text)
            self.assertIn("Apply gating", text)
            self.assertNotIn("secrets: inherit", text)

    def test_all_provider_doc_drift_steps_enable_debug_without_changing_reports(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            with self.subTest(provider=provider):
                self.assertEqual(text.count("python3 -m panopticon.drift"), 1)
                self.assertIn("--debug", text)
                self.assertIn("--report-file /tmp/panopticon-reports/drift.md", text)
                self.assertIn("--actions-file /tmp/panopticon-reports/drift-actions.json", text)

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
        self.assertIn("aws-actions/configure-aws-credentials@v6.2.3", text)
        self.assertIn("credential_mode:", text)
        self.assertIn("inputs.credential_mode == 'github-oidc'", text)
        self.assertIn("inputs.credential_mode == 'instance-managed'", text)
        self.assertIn(".github/actions/panopticon-aws-credentials/action.yml", text)
        self.assertIn("actions/setup-python@v7.0.0", text)
        self.assertIn("pip install --upgrade -r", text)
        self.assertIn("requirements-bedrock.txt", text)
        self.assertNotIn("secrets.api_key", text)
        self.assertNotIn("inputs.endpoint", text)
        self.assertNotIn("PANOPTICON_LLM_API_KEY", text)
        self.assertNotIn("PANOPTICON_LLM_ENDPOINT", text)

    def test_bedrock_credential_failure_has_a_surviving_caller_recovery_boundary(self):
        text = self.workflow("panopticon-pr-bedrock.yml")
        credential_step = text.index("id: instance_credentials")
        recovery_step = text.index("- name: Report instance-managed credential failure")
        identity_step = text.index("- name: Verify caller cloud identity")
        preflight_step = text.index("- name: Provider preflight")
        self.assertIn("timeout-minutes: 1\n        uses: ./.panopticon-instance/.github/actions/panopticon-aws-credentials", text)
        self.assertIn(
            "if: always() && steps.init.outputs.initialized == 'true' && inputs.credential_mode == 'instance-managed'",
            text,
        )
        self.assertIn("steps.instance_credentials.outcome != 'success'", text)
        self.assertIn("steps.instance_credentials.outcome != 'skipped'", text)
        self.assertIn("from panopticon.recovery import credential_action_recovery", text)
        self.assertIn("Panopticon gate 3 failed: caller identity and credentials", text)
        self.assertIn("aws sts get-caller-identity --output json", text)
        self.assertIn("Panopticon gate 3 passed: caller identity and credentials", text)
        self.assertLess(credential_step, recovery_step)
        self.assertLess(recovery_step, identity_step)
        self.assertLess(identity_step, preflight_step)

    def test_bedrock_failure_guidance_is_public_safe(self):
        text = self.workflow("panopticon-pr-bedrock.yml")
        for organization_value in ("YotpoLtd", "402837048690", "YotpoLtd/", "yotpo-api"):
            self.assertNotIn(organization_value, text)

    def test_bedrock_recovery_fallback_matches_shared_recovery_contract(self):
        text = self.workflow("panopticon-pr-bedrock.yml")
        for marker in (
            "docs/examples/panopticon-aws-credentials/action.yml",
            ".github/actions/panopticon-aws-credentials/action.yml",
            '"protected_paths": [',
            "automatically protects this fixed path during template sync",
            "PANOPTICON_AWS_REGION",
            "PANOPTICON_INSTANCE='",
        ):
            self.assertIn(marker, text)

    def test_bedrock_recovery_fallback_uses_one_workflow_path_binding(self):
        text = self.workflow("panopticon-pr-bedrock.yml")
        path = ".github/actions/panopticon-aws-credentials/action.yml"
        self.assertIn(f"PANOPTICON_CREDENTIAL_ACTION: {path}", text)
        self.assertIn('action_path = os.environ["PANOPTICON_CREDENTIAL_ACTION"]', text)
        self.assertIn('action="$PANOPTICON_INSTANCE_DIR/$PANOPTICON_CREDENTIAL_ACTION"', text)
        self.assertNotIn(f'action_path = "{path}"', text)

    def test_public_credential_action_example_is_placeholder_safe(self):
        example = (ROOT / "docs" / "examples" / "panopticon-aws-credentials" / "action.yml").read_text(encoding="utf-8")
        for marker in (
            "using: composite",
            "organization-broker",
            "PANOPTICON_AWS_REGION",
            "aws_region",
            "Replace this step",
        ):
            self.assertIn(marker, example)
        for organization_value in ("YotpoLtd", "402837048690", "yotpo-api"):
            self.assertNotIn(organization_value, example)
        self.assertNotIn("AWS_ACCESS_KEY_ID=", example)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY=", example)

    def test_public_four_gate_guidance_is_self_contained_and_safe(self):
        getting_started = (ROOT / "PANOPTICON.md").read_text(encoding="utf-8")
        setup_guide = (ROOT / "docs" / "setup-guide.md").read_text(encoding="utf-8")
        self.assertIn("](docs/setup-guide.md)", getting_started)
        for phrase in (
            "Four-gate rollout and troubleshooting",
            "Reusable-workflow access",
            "Effective provider configuration",
            "Caller-repository identity and credentials",
            "Real provider-request compatibility",
            "actions/permissions/access",
            "Administration: Read",
            "Contents: Read",
            "HTTP 403",
            "--jq '.access_level'",
            "settings/actions",
            "Protected-path debt register",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, setup_guide)
        self.assertNotIn("YotpoLtd", setup_guide)
        self.assertNotIn("402837048690", setup_guide)
        self.assertNotIn("yotpo-api", setup_guide)
        self.assertIn("Wire the four caller GitHub Actions workflows", setup_guide)
        self.assertNotIn("Wire the three caller GitHub Actions workflows", setup_guide)
        self.assertNotIn("github_owned_allowed,plan", setup_guide)

    def test_openai_workflow_is_a_standalone_litellm_clone_with_openai_identity(self):
        text = self.workflow("panopticon-pr-openai.yml")
        self.assertIn("PANOPTICON_LLM_PROVIDER: openai", text)
        self.assertNotIn("PANOPTICON_LLM_ENDPOINT", text)
        self.assertIn("Provider: `OpenAI`", text)
        self.assertNotIn("uses: ./.github/workflows/panopticon-pr-litellm.yml", text)
        self.assertNotIn("requirements-bedrock.txt", text)
        self.assertNotIn("inputs.endpoint", text)
        self.assertNotIn("endpoint:\n        required:", text)

    def test_optional_request_budgets_remain_raw_until_the_shared_resolver_runs(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            for input_name, default in REQUEST_BUDGET_DEFAULTS.items():
                with self.subTest(provider=provider, input_name=input_name):
                    self.assertIn(f"${{{{ inputs.{input_name} }}}}", text)
            self.assertIn("panopticon-provider-defaults", text)
            self.assertIn("python3 -m panopticon.provider_defaults", text)

    def test_fixed_default_action_has_a_closed_nonsecret_output_contract(self):
        text = DEFAULTS_ACTION.read_text(encoding="utf-8")
        self.assertIn("outputs:", text)
        for logical in REQUEST_BUDGET_DEFAULTS:
            with self.subTest(logical=logical):
                self.assertIn(f"  {logical}:", text)
        self.assertNotIn("inputs:", text)
        self.assertNotIn("secrets:", text)

    def test_provider_workflows_explain_a_missing_fixed_action(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            with self.subTest(provider=provider):
                self.assertIn("Panopticon provider defaults action is missing", text)
                self.assertIn(
                    ".github/actions/panopticon-provider-defaults/action.yml", text
                )

    def test_effective_values_resolve_before_provider_preflight(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            with self.subTest(provider=provider):
                self.assertLess(
                    text.index("- name: Resolve effective provider values"),
                    text.index("- name: Provider preflight"),
                )

    def test_doc_drift_exit_codes_keep_invalid_verdicts_operational(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            with self.subTest(provider=provider):
                self.assertIn('if [ "$status" -ne 0 ] && [ "$status" -ne 2 ]; then', text)
                self.assertIn('echo "error=true" >> "$GITHUB_OUTPUT"', text)
                self.assertIn('echo "stale=false" >> "$GITHUB_OUTPUT"', text)
                self.assertIn('echo "stale=$([ "$status" -eq 2 ] && echo true || echo false)"', text)

    def test_llm_wrapper_errors_are_deferred_to_final_gate(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            with self.subTest(provider=provider):
                self.assertNotIn("echo \"::error::Panopticon doc-drift check could not run", text)
                self.assertNotIn("echo \"::error::Panopticon index-currency check could not run", text)
                self.assertIn("fail \"Panopticon doc-drift check could not run", text)
                self.assertIn("fail \"Panopticon index-currency check could not run", text)

    def test_tooling_currency_has_one_aggregate_warning_and_summary_output(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            with self.subTest(provider=provider):
                self.assertIn("--summary-file \"$GITHUB_STEP_SUMMARY\"", text)
                self.assertIn("one aggregate", text.lower())

    def test_candidate_analysis_and_child_gating_are_wired_for_every_provider(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            with self.subTest(provider=provider):
                self.assertIn("- name: Interface candidate analysis (advisory)", text)
                self.assertIn("id: matching", text)
                self.assertIn("python3 -m panopticon.candidate_matching", text)
                self.assertIn("effective_gating_mode", text)
                self.assertIn("GATE_CONFLICT_SOURCE", text)
                self.assertIn("extract_diagram_block", text)
                self.assertIn("MATCH_ERROR", text)
                self.assertIn("effective policy: $GATE_CONFLICT", text)

    def test_legacy_guard_prints_configuration_and_exact_bootstrap_commands(self):
        text = self.workflow("panopticon-pr.yml")
        self.assertNotIn("panopticon.drift", text)
        for provider in ("litellm", "openai", "bedrock"):
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
            "openai": ("api_key_name:",),
            "bedrock": (
                "credential_mode:",
                "aws_region_variable_name:",
                "aws_role_arn_variable_name:",
            ),
        }
        excluded_provider_inputs = {
            "litellm": expected_provider_inputs["bedrock"],
            "openai": expected_provider_inputs["bedrock"] + ("endpoint_variable_name:",),
            "bedrock": expected_provider_inputs["litellm"],
        }
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"configure-panopticon-{provider}.yml")
            self.assertIn(f"provider: {provider}", text)
            self.assertNotIn("job_timeout_minutes_default", text)
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
        self.assertIn("Panopticon gate 2 failed: effective provider configuration", text)
        self.assertIn("Expected resource: `panopticon.config.json`", text)
        self.assertIn("generated caller revisions are per child", text)
        self.assertIn("Panopticon gate 2 passed: effective provider configuration", text)
        self.assertIn("GITHUB_STEP_SUMMARY", text)
        self.assertIn("No credential values were accepted or persisted", text)
        self.assertIn("required organization-level Actions names", text)
        self.assertIn("Optional request-budget variables", text)
        self.assertIn("optional request-budget variable", text)
        self.assertIn("Job timeout ", text)
        self.assertIn("reusable-workflow fallback because", text)
        self.assertNotIn(
            "Leave an optional variable empty to use the fixed instance Action",
            text,
        )
        self.assertNotIn("job-timeout-minutes-default", text)
        self.assertNotIn("JOB_TIMEOUT_MINUTES_DEFAULT", text)
        self.assertIn("git diff --quiet -- panopticon.config.json", text)
        self.assertIn("Configuration already matches", text)
        self.assertIn("could not be pushed", text)
        self.assertIn("git show --format= -- panopticon.config.json", text)
        self.assertIn("exit 1", text)
        self.assertIn('print(f"::error::{reason}; see the step summary")', text)
        self.assertNotIn(
            'raise SystemExit(f"::error::{reason}; see the step summary")', text
        )

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
        self.assertIn(
            'print(f"::error::{reason}; see the step summary")', configuration_action
        )
        self.assertIn(
            'print(f"::error::{reason}; see the step summary")',
            self.workflow("panopticon-pr-bedrock.yml"),
        )

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
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            self.assertIn("caller compatibility revision changed", text)
            self.assertIn(
                'expected not in {actual["caller_revision"], actual["legacy_revision"]}',
                text,
            )
            self.assertIn("from panopticon.recovery import stale_caller_recovery", text)
            self.assertIn("from panopticon.recovery import missing_provider_recovery", text)
            self.assertIn("except ModuleNotFoundError", text)

    def test_legacy_callers_can_dispatch_to_the_revision_gate(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            self.assertIn(
                "configuration_defaults:\n"
                "        description: Legacy caller mapping retained only for migration; ignored.\n"
                "        required: false\n"
                "        type: string\n"
                "        default: \"{}\"",
                text,
            )
            self.assertIn("default: \"{}\"", text)
            gate = text.split("- name: Validate provider configuration revision", 1)[1]
            self.assertIn('actual["legacy_revision"]', gate)
            self.assertNotIn("inputs.configuration_defaults", gate)

    def test_provider_configuration_failures_identify_gate_two(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            self.assertIn("Panopticon gate 2 failed: effective provider configuration", text)
            self.assertIn("Panopticon provider defaults action is missing", text)

    def test_bedrock_configuration_exposes_a_non_secret_model_default(self):
        workflow = self.workflow("configure-panopticon-bedrock.yml")
        configuration_action = CONFIGURATION_ACTION.read_text(encoding="utf-8")
        self.assertIn("model_default:", workflow)
        self.assertIn("model-default: ${{ inputs.model_default }}", workflow)
        self.assertIn("MODEL_DEFAULT: ${{ inputs.model-default }}", configuration_action)
        self.assertIn('"model": "MODEL_DEFAULT"', configuration_action)
        self.assertIn("llm.defaults.model", configuration_action)

    def test_configuration_summary_derives_optionality_without_persisting_it(self):
        action = CONFIGURATION_ACTION.read_text(encoding="utf-8")
        self.assertIn("resolve_provider_contract(configured)", action)
        self.assertIn('contract["optional_variables"]', action)
        self.assertNotIn('configured["optional_variables"]', action)

    def test_legacy_guard_retains_a_self_contained_recovery_fallback(self):
        text = self.workflow("panopticon-pr.yml")
        self.assertNotIn("panopticon.recovery", text)
        self.assertIn("PANOPTICON_INSTANCE='{instance}' python3", text)

    def test_feature_dispatch_is_fixed_and_blocking_mode_reaches_final_gate(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            self.assertIn("python3 -m panopticon.features check", text)
            self.assertIn("PANOPTICON_FEATURE_GATE=blocking-failed", text)
            self.assertIn("Panopticon blocking feature check found documentation violations", text)
            self.assertNotIn("feature:", text.split("workflow_call:", 1)[1].split("jobs:", 1)[0])
            self.assertNotIn("feature_mode:", text)

    def test_pinned_ref_warning_names_both_refs_and_exact_refresh_action(self):
        for provider in ("litellm", "openai", "bedrock"):
            text = self.workflow(f"panopticon-pr-{provider}.yml")
            warning = text.split("- name: Warn about pinned workflow ref currency", 1)[1]
            self.assertIn("actual", warning)
            self.assertIn("configured", warning)
            self.assertIn("python3 -m panopticon.sync", warning)
            self.assertIn("does not infer a latest tag", warning)

    def test_generic_feature_configuration_has_no_secret_inputs(self):
        workflow = self.workflow("configure-panopticon-features.yml")
        action = (ROOT / ".github" / "actions" / "configure-panopticon-features" / "action.yml").read_text()
        self.assertIn("feature:", workflow)
        self.assertIn("mode:", workflow)
        self.assertIn("configure_feature", action)
        self.assertNotIn("secrets:", workflow)
        self.assertNotIn("secrets:", action)


if __name__ == "__main__":
    unittest.main()
