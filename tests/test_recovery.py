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
        self.assertIn(
            "https://github.com/acme/private-instance/actions/workflows/configure-panopticon.yml",
            text,
        )
        self.assertIn(
            "gh workflow run configure-panopticon.yml --repo acme/private-instance --ref trunk",
            text,
        )
        self.assertIn(
            "PANOPTICON_INSTANCE='acme/private-instance' python3",
            text,
        )
        self.assertNotIn("export PANOPTICON_INSTANCE", text)

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


if __name__ == "__main__":
    unittest.main()
