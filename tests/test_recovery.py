"""Exact-output tests for provider recovery guidance."""

import unittest

from panopticon.recovery import (
    child_bootstrap_command,
    configuration_recovery,
    missing_provider_recovery,
    stale_caller_recovery,
)


class TestRecoveryOutput(unittest.TestCase):
    def test_configuration_recovery_has_console_cli_and_bootstrap_paths(self):
        text = configuration_recovery("acme/private-instance", "trunk")
        for provider in ("litellm", "bedrock"):
            self.assertIn(
                "https://github.com/acme/private-instance/actions/workflows/"
                f"configure-panopticon-{provider}.yml",
                text,
            )
            self.assertIn(
                f"gh workflow run configure-panopticon-{provider}.yml "
                "--repo acme/private-instance --ref trunk",
                text,
            )
        self.assertIn(
            "PANOPTICON_INSTANCE='acme/private-instance' python3",
            text,
        )
        self.assertNotIn("export PANOPTICON_INSTANCE", text)
        self.assertNotIn("select-a-provider", text)

    def test_private_instance_recovery_uses_its_custom_branch_everywhere(self):
        instance = "acme/private-instance"
        branch = "release/2026-07"
        self.assertEqual(
            configuration_recovery(instance, branch),
            "Configure the Panopticon instance before bootstrapping a child repository.\n\n"
            "GitHub Actions console (choose exactly one provider):\n"
            "  LiteLLM: https://github.com/acme/private-instance/actions/workflows/"
            "configure-panopticon-litellm.yml\n"
            "  Bedrock: https://github.com/acme/private-instance/actions/workflows/"
            "configure-panopticon-bedrock.yml\n"
            "  1. Open the workflow for the provider the instance will use.\n"
            "  2. Select Run workflow.\n"
            "  3. Select branch release/2026-07.\n"
            "  4. Review the secret and variable name fields; enter names only, never values.\n"
            "  5. Select Run workflow and wait for the green completed run that commits "
            "panopticon.config.json.\n\n"
            "Equivalent GitHub CLI commands (run exactly one):\n"
            "  gh workflow run configure-panopticon-litellm.yml --repo acme/private-instance "
            "--ref release/2026-07\n"
            "  gh workflow run configure-panopticon-bedrock.yml --repo acme/private-instance "
            "--ref release/2026-07\n"
            "  gh run watch --repo acme/private-instance\n\n"
            "Then rerun child bootstrap from inside the child repository clone:\n"
            "  curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/"
            "panopticon-ay-eye/main/install.py | "
            "PANOPTICON_INSTANCE='acme/private-instance' python3\n",
        )

    def test_missing_provider_recovery_names_missing_values_and_exact_command(self):
        text = missing_provider_recovery(
            "acme/instance",
            "Bedrock",
            [("aws_region", "CUSTOM_AWS_REGION"), ("model", "CUSTOM_MODEL")],
        )
        self.assertIn("## Panopticon: missing Bedrock configuration", text)
        self.assertIn("- `CUSTOM_AWS_REGION` (aws_region)", text)
        self.assertIn("- `CUSTOM_MODEL` (model)", text)
        self.assertIn(child_bootstrap_command("acme/instance"), text)
        self.assertIn("Review and commit the generated changes, push them", text)

    def test_stale_caller_recovery_preserves_secret_rotation_guidance(self):
        text = stale_caller_recovery("acme/instance")
        self.assertIn("## Panopticon child caller is stale", text)
        self.assertIn(child_bootstrap_command("acme/instance"), text)
        self.assertIn("Keep old secret names available until regeneration finishes.", text)

    def test_stale_provider_or_name_change_recovery_is_exact(self):
        self.assertEqual(
            stale_caller_recovery("acme/instance"),
            "## Panopticon child caller is stale\n\n"
            "Run this from inside the child clone:\n\n"
            "~~~bash\n"
            "curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/"
            "panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='acme/instance' python3\n"
            "~~~\n\n"
            "Review and commit the generated changes, push them, then rerun or await this PR workflow. "
            "Keep old secret names available until regeneration finishes.\n",
        )


if __name__ == "__main__":
    unittest.main()
