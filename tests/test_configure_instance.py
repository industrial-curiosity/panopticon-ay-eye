"""Instance provider configuration writes validated names and preserves unrelated settings."""

import contextlib
import json
from io import StringIO
import tempfile
import unittest
from pathlib import Path

from panopticon.configure_instance import configure, main
from panopticon.providers import ProviderConfigError, resolve_provider_contract


class TestConfigureInstance(unittest.TestCase):
    @staticmethod
    def litellm_names():
        return {
            "instance_token": "PANOPTICON_INSTANCE_TOKEN",
            "api_key": "PANOPTICON_LLM_API_KEY",
            "model": "PANOPTICON_LLM_MODEL",
            "timeout_seconds": "PANOPTICON_LLM_TIMEOUT_SECONDS",
            "max_attempts": "PANOPTICON_LLM_MAX_ATTEMPTS",
            "max_correction_attempts": "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS",
            "job_timeout_minutes": "PANOPTICON_LLM_JOB_TIMEOUT_MINUTES",
            "endpoint": "PANOPTICON_LLM_ENDPOINT",
        }

    def test_bedrock_defaults_are_persisted_without_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon.config.json"
            path.write_text('{"schema_version": 1, "gating": {"init": "blocking"}}\n')
            llm = configure(
                tmp,
                "bedrock",
                {
                    "instance_token": "PANOPTICON_INSTANCE_TOKEN",
                    "model": "PANOPTICON_LLM_MODEL",
                    "timeout_seconds": "PANOPTICON_LLM_TIMEOUT_SECONDS",
                    "max_attempts": "PANOPTICON_LLM_MAX_ATTEMPTS",
                    "max_correction_attempts": "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS",
                    "job_timeout_minutes": "PANOPTICON_LLM_JOB_TIMEOUT_MINUTES",
                    "aws_region": "PANOPTICON_AWS_REGION",
                    "aws_role_arn": "PANOPTICON_AWS_ROLE_ARN",
                },
            )
            document = json.loads(path.read_text())
        self.assertEqual(llm["provider"], "bedrock")
        self.assertEqual(document["gating"], {"init": "blocking"})
        self.assertNotIn("value", json.dumps(document).lower())

    def test_unknown_provider_does_not_modify_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon.config.json"
            path.write_text('{"schema_version": 1}\n')
            before = path.read_bytes()
            with self.assertRaises(ProviderConfigError):
                configure(tmp, "mystery", {})
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_name_does_not_modify_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon.config.json"
            path.write_text('{"schema_version": 1}\n')
            before = path.read_bytes()
            names = {
                "instance_token": "PANOPTICON_INSTANCE_TOKEN",
                "api_key": "actual-secret-value",
                "model": "PANOPTICON_LLM_MODEL",
                "timeout_seconds": "PANOPTICON_LLM_TIMEOUT_SECONDS",
                "max_attempts": "PANOPTICON_LLM_MAX_ATTEMPTS",
                "max_correction_attempts": "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS",
                "job_timeout_minutes": "PANOPTICON_LLM_JOB_TIMEOUT_MINUTES",
                "endpoint": "PANOPTICON_LLM_ENDPOINT",
            }
            with self.assertRaises(ProviderConfigError):
                configure(tmp, "litellm", names)
            self.assertEqual(path.read_bytes(), before)

    def test_unknown_logical_name_does_not_modify_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon.config.json"
            path.write_text('{"schema_version": 1}\n')
            before = path.read_bytes()
            names = self.litellm_names()
            names["api_key_value"] = "must-not-be-accepted"
            with self.assertRaisesRegex(ProviderConfigError, "unknown logical names"):
                configure(tmp, "litellm", names)
            self.assertEqual(path.read_bytes(), before)

    def test_defaults_fill_omitted_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            llm = configure(tmp, "bedrock", {})
        self.assertEqual(llm["secrets"]["instance_token"], "PANOPTICON_INSTANCE_TOKEN")
        self.assertEqual(llm["variables"]["aws_region"], "PANOPTICON_AWS_REGION")

    def test_instance_managed_bedrock_needs_no_aws_variable_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            llm = configure(tmp, "bedrock", {}, "instance-managed")
        self.assertEqual(llm["credential_mode"], "instance-managed")
        self.assertNotIn("aws_region", llm["variables"])
        self.assertNotIn("aws_role_arn", llm["variables"])

    def test_equivalent_rerun_is_byte_for_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            configure(tmp, "litellm", self.litellm_names())
            path = Path(tmp) / "panopticon.config.json"
            first = path.read_bytes()
            configure(tmp, "litellm", self.litellm_names())
            self.assertEqual(path.read_bytes(), first)

    def test_workflow_split_does_not_change_effective_contract_revision(self):
        expected = resolve_provider_contract({"provider": "litellm"})["revision"]
        with tempfile.TemporaryDirectory() as tmp:
            configured = configure(tmp, "litellm", self.litellm_names())
        self.assertEqual(resolve_provider_contract(configured)["revision"], expected)

    def test_cli_rejects_unknown_provider_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon.config.json"
            path.write_text('{"schema_version": 1}\n')
            with contextlib.redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    main(["--instance-root", tmp, "--provider", "mystery"])
            self.assertEqual(ctx.exception.code, 2)
            self.assertEqual(json.loads(path.read_text()), {"schema_version": 1})


if __name__ == "__main__":
    unittest.main()
