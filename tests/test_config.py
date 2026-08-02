"""Org and repo configuration: defaults, overrides in both directions, initialization flag."""

import json
import tempfile
import unittest
from pathlib import Path

from panopticon.config import (
    ConfigError,
    DEFAULT_DIAGRAM_FORMAT,
    DEFAULT_GATING,
    DIAGRAM_CONFIG_BASENAME,
    PROTECTED_CONFIG_FILES,
    gating_mode,
    load_diagram_config,
    load_org_config,
    load_repo_config,
    provider_contract,
    require_supported_diagram_format,
    save_repo_config,
)
from panopticon.providers import (
    PROVIDERS,
    ProviderConfigError,
    resolve_effective_values,
    resolve_provider_contract,
)
from panopticon.provider_defaults import resolve_for_workflow


class TestOrgConfig(unittest.TestCase):
    def write_config(self, tmp, doc):
        (Path(tmp) / "panopticon.config.json").write_text(json.dumps(doc))

    def test_missing_file_yields_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_org_config(tmp)
        self.assertEqual(config["gating"], DEFAULT_GATING)
        # No network access here, so there's no way to know the instance's default branch —
        # None signals "not pinned locally" rather than guessing a tag that may not exist.
        self.assertIsNone(config["workflow_ref"])
        self.assertIsNone(config["llm"])

    def test_unconfigured_template_loads_but_provider_resolution_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_org_config(tmp)
        with self.assertRaisesRegex(ProviderConfigError, "no LLM provider"):
            provider_contract(config)

    def test_litellm_provider_defaults_are_resolved(self):
        contract = resolve_provider_contract({"provider": "litellm"})
        self.assertEqual(contract["workflow"], "panopticon-pr-litellm.yml")

    def test_workflow_resolution_reports_the_pre_job_timeout_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"llm": {"provider": "openai"}})
            values, sources = resolve_for_workflow(
                tmp,
                {
                    "PANOPTICON_LLM_MODEL": "gpt-test",
                    "PANOPTICON_JOB_TIMEOUT_SOURCE": "organization variable",
                },
            )
        self.assertEqual(values["model"], "gpt-test")
        self.assertEqual(sources["job_timeout_minutes"], "organization variable")

    def test_openai_provider_defaults_are_resolved(self):
        contract = resolve_provider_contract({"provider": "openai"})
        self.assertEqual(contract["workflow"], "panopticon-pr-openai.yml")
        self.assertEqual(contract["endpoint"], "https://api.openai.com/v1")
        self.assertEqual(contract["secrets"]["api_key"], "PANOPTICON_LLM_API_KEY")
        self.assertNotIn("endpoint", contract["variables"])
        self.assertNotIn("id-token", contract["permissions"])

    def test_openai_rejects_an_endpoint_variable_override(self):
        with self.assertRaisesRegex(ProviderConfigError, "unknown logical names"):
            resolve_provider_contract(
                {"provider": "openai", "variables": {"endpoint": "OTHER_ENDPOINT"}}
            )

    def test_bedrock_provider_has_oidc_contract(self):
        contract = resolve_provider_contract({"provider": "bedrock"})
        self.assertEqual(contract["workflow"], "panopticon-pr-bedrock.yml")
        self.assertEqual(contract["permissions"]["id-token"], "write")
        self.assertEqual(contract["variables"]["aws_region"], "PANOPTICON_AWS_REGION")
        self.assertEqual(contract["dependencies"], ["boto3==1.43.51"])

    def test_bedrock_instance_managed_contract_has_no_oidc_variables(self):
        contract = resolve_provider_contract(
            {"provider": "bedrock", "credential_mode": "instance-managed"}
        )
        self.assertEqual(contract["credential_mode"], "instance-managed")
        self.assertNotIn("aws_region", contract["variables"])
        self.assertNotIn("aws_role_arn", contract["variables"])
        self.assertEqual(
            contract["credential_action"],
            ".github/actions/panopticon-aws-credentials/action.yml",
        )

    def test_bedrock_rejects_unknown_credential_mode(self):
        with self.assertRaisesRegex(ProviderConfigError, "unknown Bedrock credential mode"):
            resolve_provider_contract({"provider": "bedrock", "credential_mode": "untrusted"})

    def test_unknown_provider_names_supported_values(self):
        with self.assertRaises(ProviderConfigError) as ctx:
            resolve_provider_contract({"provider": "mystery"})
        for provider in PROVIDERS:
            self.assertIn(provider, str(ctx.exception))

    def test_unknown_provider_config_field_is_rejected(self):
        with self.assertRaisesRegex(ProviderConfigError, "unknown fields"):
            resolve_provider_contract({"provider": "litellm", "workflow": "arbitrary.yml"})

    def test_revision_changes_when_caller_relevant_name_changes(self):
        original = resolve_provider_contract({"provider": "litellm"})
        renamed = resolve_provider_contract(
            {"provider": "litellm", "secrets": {"api_key": "ACME_LLM_KEY"}}
        )
        self.assertNotEqual(original["revision"], renamed["revision"])

    def test_revision_is_stable_for_equivalent_contracts(self):
        first = resolve_provider_contract({"provider": "bedrock"})
        second = resolve_provider_contract({"provider": "bedrock", "variables": {}})
        self.assertEqual(first["revision"], second["revision"])

    def test_optional_defaults_change_contract_revision(self):
        original = resolve_provider_contract({"provider": "litellm"})
        configured = resolve_provider_contract(
            {"provider": "litellm", "defaults": {"timeout_seconds": "45"}}
        )
        self.assertNotEqual(original["revision"], configured["revision"])

    def test_default_for_required_value_is_rejected(self):
        with self.assertRaisesRegex(ProviderConfigError, "defaults"):
            resolve_provider_contract({"provider": "litellm", "defaults": {"model": "x"}})

    def test_runtime_effective_values_use_source_precedence(self):
        contract = resolve_provider_contract(
            {"provider": "litellm", "defaults": {"timeout_seconds": "45"}}
        )
        values, sources = resolve_effective_values(
            contract,
            {"model": "model", "endpoint": "https://example.test", "timeout_seconds": "30"},
            {"timeout_seconds": "15", "max_attempts": "7"},
        )
        self.assertEqual(values["timeout_seconds"], "30")
        self.assertEqual(sources["timeout_seconds"], "organization variable")
        self.assertEqual(values["max_attempts"], "7")
        self.assertEqual(sources["max_attempts"], "instance action")
        self.assertEqual(values["max_correction_attempts"], "2")
        self.assertEqual(sources["max_correction_attempts"], "workflow default")

    def test_required_runtime_value_cannot_use_a_default(self):
        contract = resolve_provider_contract({"provider": "openai"})
        with self.assertRaisesRegex(ProviderConfigError, "model"):
            resolve_effective_values(contract, {})

    def test_workflow_resolver_uses_instance_default_without_exposing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(
                tmp,
                {"llm": {"provider": "openai", "defaults": {"timeout_seconds": "45"}}},
            )
            values, sources = resolve_for_workflow(
                tmp,
                {
                    "PANOPTICON_LLM_MODEL": "gpt-4o-mini",
                    "PANOPTICON_LLM_TIMEOUT_SECONDS": "",
                    "PANOPTICON_LLM_MAX_ATTEMPTS": "",
                    "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS": "",
                },
            )
        self.assertEqual(values["timeout_seconds"], "45")
        self.assertEqual(sources["timeout_seconds"], "instance config")

    def test_invalid_actions_name_is_rejected(self):
        with self.assertRaisesRegex(ProviderConfigError, "GitHub Actions name"):
            resolve_provider_contract(
                {"provider": "litellm", "secrets": {"api_key": "sk-secret-value"}}
            )

    def test_workflow_ref_is_read_through_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"workflow_ref": "v2"})
            config = load_org_config(tmp)
        self.assertEqual(config["workflow_ref"], "v2")

    def test_default_gating_policy(self):
        self.assertEqual(DEFAULT_GATING["init"], "blocking")
        self.assertEqual(DEFAULT_GATING["doc-drift"], "blocking")
        self.assertEqual(DEFAULT_GATING["interface-conflict"], "advisory")
        # Advisory at first so existing initialized repos aren't immediately blocked before
        # they've backfilled a diagram section (migration plan).
        self.assertEqual(DEFAULT_GATING["diagram-missing"], "advisory")

    def test_org_can_escalate_and_downgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(
                tmp, {"gating": {"interface-conflict": "blocking", "doc-drift": "advisory"}}
            )
            config = load_org_config(tmp)
        self.assertEqual(gating_mode(config, "interface-conflict"), "blocking")
        self.assertEqual(gating_mode(config, "doc-drift"), "advisory")
        self.assertEqual(gating_mode(config, "init"), "blocking")

    def test_protected_paths_defaults_to_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_org_config(tmp)
        self.assertEqual(config["protected_paths"], [])

    def test_protected_paths_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(
                tmp, {"protected_paths": [".agents/skills/panopticon-foo/SKILL.md", "panopticon/docs.py"]}
            )
            config = load_org_config(tmp)
        self.assertEqual(
            config["protected_paths"],
            [".agents/skills/panopticon-foo/SKILL.md", "panopticon/docs.py"],
        )

    def test_protected_paths_rejects_non_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"protected_paths": "not-a-list"})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_protected_paths_rejects_empty_string_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"protected_paths": [""]})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_protected_paths_rejects_non_string_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"protected_paths": [123]})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_internal_registries_defaults_to_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_org_config(tmp)
        self.assertEqual(config["internal_registries"], [])

    def test_internal_registries_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"internal_registries": ["packages.example.com", "npm.example.com"]})
            config = load_org_config(tmp)
        self.assertEqual(
            config["internal_registries"],
            ["packages.example.com", "npm.example.com"],
        )

    def test_internal_registries_rejects_non_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"internal_registries": "not-a-list"})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_internal_registries_rejects_empty_string_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"internal_registries": [""]})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_internal_registries_rejects_non_string_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"internal_registries": [123]})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_unknown_check_type_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"gating": {"linting": "blocking"}})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_invalid_mode_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"gating": {"init": "maybe"}})
            with self.assertRaises(ConfigError):
                load_org_config(tmp)

    def test_template_root_config_matches_defaults(self):
        repo_root = Path(__file__).resolve().parent.parent
        config = load_org_config(repo_root)
        self.assertEqual(config["gating"], DEFAULT_GATING)

    def test_template_root_config_ships_no_pinned_workflow_ref(self):
        # The template repo has no release-tagging process, so a workflow_ref committed here
        # would never correspond to a real git ref — and "Use this template" copies this file
        # verbatim into every new instance, silently breaking caller-workflow resolution for all
        # of them from their first bootstrap. Regression test for that exact fossil.
        repo_root = Path(__file__).resolve().parent.parent
        raw = json.loads((repo_root / "panopticon.config.json").read_text())
        self.assertNotIn("workflow_ref", raw)

    def test_template_root_config_ships_without_provider_selection(self):
        repo_root = Path(__file__).resolve().parent.parent
        raw = json.loads((repo_root / "panopticon.config.json").read_text())
        self.assertNotIn("llm", raw)


class TestRepoConfig(unittest.TestCase):
    def test_uninitialized_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_repo_config(tmp))

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_repo_config(
                {
                    "repo": "svc-a",
                    "instance": "acme/panopticon-instance",
                    "workflow_ref": "v1",
                    "docs_location": "docs",
                },
                repo_root=tmp,
            )
            config = load_repo_config(tmp)
        self.assertEqual(config["repo"], "svc-a")
        self.assertEqual(config["schema_version"], 1)

    def test_incomplete_config_is_a_loud_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panopticon"
            path.mkdir()
            (path / "config.json").write_text(json.dumps({"repo": "svc-a"}))
            with self.assertRaises(ConfigError) as ctx:
                load_repo_config(tmp)
        self.assertIn("instance", str(ctx.exception))


class TestDiagramConfig(unittest.TestCase):
    def write_config(self, tmp, doc):
        (Path(tmp) / DIAGRAM_CONFIG_BASENAME).write_text(json.dumps(doc))

    def test_missing_file_yields_mermaid_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_diagram_config(tmp)
        self.assertEqual(config, {"format": DEFAULT_DIAGRAM_FORMAT})

    def test_instance_overrides_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"format": "plantuml"})
            config = load_diagram_config(tmp)
        self.assertEqual(config["format"], "plantuml")

    def test_unknown_top_level_field_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"format": "mermaid", "extra": True})
            with self.assertRaises(ConfigError):
                load_diagram_config(tmp)

    def test_empty_format_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_config(tmp, {"format": ""})
            with self.assertRaises(ConfigError):
                load_diagram_config(tmp)

    def test_supported_format_passes(self):
        require_supported_diagram_format(DEFAULT_DIAGRAM_FORMAT)  # does not raise

    def test_unsupported_format_fails_loudly(self):
        with self.assertRaises(ConfigError) as ctx:
            require_supported_diagram_format("plantuml")
        self.assertIn("plantuml", str(ctx.exception))

    def test_protected_config_registry_contains_diagram_config(self):
        self.assertIn(DIAGRAM_CONFIG_BASENAME, PROTECTED_CONFIG_FILES)
        self.assertEqual(
            PROTECTED_CONFIG_FILES[DIAGRAM_CONFIG_BASENAME], {"format": DEFAULT_DIAGRAM_FORMAT}
        )


if __name__ == "__main__":
    unittest.main()
