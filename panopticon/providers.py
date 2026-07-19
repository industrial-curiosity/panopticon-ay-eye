"""Trusted LLM provider contracts for instance configuration and child workflow wiring."""

import hashlib
import json
import re


CONTRACT_VERSION = 1
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

COMMON_VARIABLES = {
    "model": "PANOPTICON_LLM_MODEL",
    "timeout_seconds": "PANOPTICON_LLM_TIMEOUT_SECONDS",
    "max_attempts": "PANOPTICON_LLM_MAX_ATTEMPTS",
    "max_correction_attempts": "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS",
    "job_timeout_minutes": "PANOPTICON_LLM_JOB_TIMEOUT_MINUTES",
}

PROVIDERS = {
    "litellm": {
        "workflow": "panopticon-pr-litellm.yml",
        "permissions": {"contents": "read", "pull-requests": "write"},
        "secrets": {
            "instance_token": "PANOPTICON_INSTANCE_TOKEN",
            "api_key": "PANOPTICON_LLM_API_KEY",
        },
        "variables": {
            **COMMON_VARIABLES,
            "endpoint": "PANOPTICON_LLM_ENDPOINT",
        },
        "dependencies": [],
    },
    "bedrock": {
        "workflow": "panopticon-pr-bedrock.yml",
        "permissions": {
            "contents": "read",
            "id-token": "write",
            "pull-requests": "write",
        },
        "secrets": {"instance_token": "PANOPTICON_INSTANCE_TOKEN"},
        "variables": {
            **COMMON_VARIABLES,
            "aws_region": "PANOPTICON_AWS_REGION",
            "aws_role_arn": "PANOPTICON_AWS_ROLE_ARN",
        },
        "dependencies": ["boto3==1.43.51"],
    },
}


class ProviderConfigError(ValueError):
    """The instance's provider contract is absent or invalid."""


def supported_providers():
    return tuple(PROVIDERS)


def validate_actions_name(value, description):
    """Validate a GitHub Actions secret or variable identifier, never a credential value."""
    if not isinstance(value, str) or not NAME_PATTERN.fullmatch(value):
        raise ProviderConfigError(
            f"{description} must be a GitHub Actions name matching {NAME_PATTERN.pattern}"
        )
    if value.upper().startswith("GITHUB_"):
        raise ProviderConfigError(f"{description} must not use the reserved GITHUB_ prefix")
    return value


def resolve_provider_contract(llm_config):
    """Return the trusted, effective provider contract or raise a loud configuration error."""
    if not llm_config:
        raise ProviderConfigError("no LLM provider is selected")
    if not isinstance(llm_config, dict):
        raise ProviderConfigError("org config 'llm' must be an object")
    unknown_fields = set(llm_config) - {"provider", "secrets", "variables"}
    if unknown_fields:
        raise ProviderConfigError(f"org config 'llm' has unknown fields: {sorted(unknown_fields)}")
    provider = llm_config.get("provider")
    if provider not in PROVIDERS:
        raise ProviderConfigError(
            f"unknown LLM provider {provider!r}; supported providers: {', '.join(PROVIDERS)}"
        )

    definition = PROVIDERS[provider]
    configured_secrets = llm_config.get("secrets", {})
    configured_variables = llm_config.get("variables", {})
    if not isinstance(configured_secrets, dict) or not isinstance(configured_variables, dict):
        raise ProviderConfigError("org config 'llm.secrets' and 'llm.variables' must be objects")

    unknown_secrets = set(configured_secrets) - set(definition["secrets"])
    unknown_variables = set(configured_variables) - set(definition["variables"])
    if unknown_secrets or unknown_variables:
        raise ProviderConfigError(
            "provider config contains unknown logical names: "
            f"secrets={sorted(unknown_secrets)}, variables={sorted(unknown_variables)}"
        )

    secrets = {
        logical: validate_actions_name(configured_secrets.get(logical, default), f"{logical} secret")
        for logical, default in definition["secrets"].items()
    }
    variables = {
        logical: validate_actions_name(
            configured_variables.get(logical, default), f"{logical} variable"
        )
        for logical, default in definition["variables"].items()
    }
    contract = {
        "contract_version": CONTRACT_VERSION,
        "provider": provider,
        "workflow": definition["workflow"],
        "permissions": dict(definition["permissions"]),
        "secrets": secrets,
        "variables": variables,
        "dependencies": list(definition["dependencies"]),
    }
    serialized = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    contract["revision"] = hashlib.sha256(serialized).hexdigest()
    return contract


def provider_config(provider, secret_names=None, variable_names=None):
    """Build the persisted provider block from validated name overrides."""
    contract = resolve_provider_contract(
        {
            "provider": provider,
            "secrets": secret_names or {},
            "variables": variable_names or {},
        }
    )
    return {
        "provider": provider,
        "secrets": contract["secrets"],
        "variables": contract["variables"],
    }
