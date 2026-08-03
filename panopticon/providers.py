"""Trusted LLM provider contracts and effective-value resolution."""

import hashlib
import json
import re


CONTRACT_VERSION = 3
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
INSTANCE_CREDENTIAL_ACTION = ".github/actions/panopticon-aws-credentials/action.yml"
INSTANCE_DEFAULTS_ACTION = ".github/actions/panopticon-provider-defaults/action.yml"

COMMON_VARIABLES = {
    "model": "PANOPTICON_LLM_MODEL",
    "timeout_seconds": "PANOPTICON_LLM_TIMEOUT_SECONDS",
    "max_attempts": "PANOPTICON_LLM_MAX_ATTEMPTS",
    "max_correction_attempts": "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS",
    "job_timeout_minutes": "PANOPTICON_LLM_JOB_TIMEOUT_MINUTES",
}

TEMPLATE_DEFAULTS = {
    "timeout_seconds": "90",
    "max_attempts": "2",
    "max_correction_attempts": "2",
    "job_timeout_minutes": "20",
}
OPTIONAL_VARIABLES = tuple(TEMPLATE_DEFAULTS)
RUNTIME_OPTIONAL_VARIABLES = tuple(
    logical for logical in OPTIONAL_VARIABLES if logical != "job_timeout_minutes"
)

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
    "openai": {
        "workflow": "panopticon-pr-openai.yml",
        "endpoint": "https://api.openai.com/v1",
        "permissions": {"contents": "read", "pull-requests": "write"},
        "secrets": {
            "instance_token": "PANOPTICON_INSTANCE_TOKEN",
            "api_key": "PANOPTICON_LLM_API_KEY",
        },
        "variables": {
            **COMMON_VARIABLES,
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
        "variables": {**COMMON_VARIABLES},
        "credential_modes": {
            "github-oidc": {
                "variables": {
                    "aws_region": "PANOPTICON_AWS_REGION",
                    "aws_role_arn": "PANOPTICON_AWS_ROLE_ARN",
                }
            },
            "instance-managed": {"variables": {}, "action": INSTANCE_CREDENTIAL_ACTION},
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
    unknown_fields = set(llm_config) - {
        "provider", "credential_mode", "secrets", "variables", "defaults"
    }
    if unknown_fields:
        raise ProviderConfigError(f"org config 'llm' has unknown fields: {sorted(unknown_fields)}")
    provider = llm_config.get("provider")
    if provider not in PROVIDERS:
        raise ProviderConfigError(
            f"unknown LLM provider {provider!r}; supported providers: {', '.join(PROVIDERS)}"
        )

    definition = PROVIDERS[provider]
    credential_mode = llm_config.get("credential_mode")
    mode_definition = {}
    if "credential_modes" in definition:
        credential_mode = credential_mode or "github-oidc"
        mode_definition = definition["credential_modes"].get(credential_mode)
        if mode_definition is None:
            raise ProviderConfigError(
                f"unknown Bedrock credential mode {credential_mode!r}; supported modes: "
                + ", ".join(definition["credential_modes"])
            )
    elif credential_mode is not None:
        raise ProviderConfigError(f"provider {provider!r} does not support a credential mode")
    configured_secrets = llm_config.get("secrets", {})
    configured_variables = llm_config.get("variables", {})
    configured_defaults = llm_config.get("defaults", {})
    if not all(isinstance(item, dict) for item in (
        configured_secrets, configured_variables, configured_defaults
    )):
        raise ProviderConfigError(
            "org config 'llm.secrets', 'llm.variables', and 'llm.defaults' must be objects"
        )

    unknown_secrets = set(configured_secrets) - set(definition["secrets"])
    variables_definition = {**definition["variables"], **mode_definition.get("variables", {})}
    unknown_variables = set(configured_variables) - set(variables_definition)
    optional_variables = tuple(
        logical for logical in OPTIONAL_VARIABLES if logical in variables_definition
    )
    invalid_defaults = set(configured_defaults) - set(optional_variables)
    if unknown_secrets or unknown_variables or invalid_defaults:
        raise ProviderConfigError(
            "provider config contains unknown logical names: "
            f"secrets={sorted(unknown_secrets)}, variables={sorted(unknown_variables)}, "
            f"defaults={sorted(invalid_defaults)}"
        )
    if not all(isinstance(value, str) and value.strip() for value in configured_defaults.values()):
        raise ProviderConfigError("provider config defaults must be non-empty strings")

    secrets = {
        logical: validate_actions_name(configured_secrets.get(logical, default), f"{logical} secret")
        for logical, default in definition["secrets"].items()
    }
    variables = {
        logical: validate_actions_name(
            configured_variables.get(logical, default), f"{logical} variable"
        )
        for logical, default in variables_definition.items()
    }
    contract = {
        "contract_version": CONTRACT_VERSION,
        "provider": provider,
        "credential_mode": credential_mode,
        "workflow": definition["workflow"],
        "permissions": dict(definition["permissions"]),
        "secrets": secrets,
        "variables": variables,
        "optional_variables": optional_variables,
        "template_defaults": {
            logical: TEMPLATE_DEFAULTS[logical] for logical in optional_variables
        },
        "defaults": dict(configured_defaults),
        "dependencies": list(definition["dependencies"]),
    }
    if "endpoint" in definition:
        contract["endpoint"] = definition["endpoint"]
    if mode_definition.get("action"):
        contract["credential_action"] = mode_definition["action"]
    if RUNTIME_OPTIONAL_VARIABLES:
        contract["default_resolver_action"] = INSTANCE_DEFAULTS_ACTION
    contract = {key: value for key, value in contract.items() if value is not None}
    serialized = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    contract["revision"] = hashlib.sha256(serialized).hexdigest()
    return contract


def provider_config(provider, secret_names=None, variable_names=None, credential_mode=None,
                    defaults=None):
    """Build the persisted provider block from validated name overrides."""
    contract = resolve_provider_contract(
        {
            "provider": provider,
            "credential_mode": credential_mode,
            "secrets": secret_names or {},
            "variables": variable_names or {},
            "defaults": defaults or {},
        }
    )
    return {
        "provider": provider,
        **(
            {"credential_mode": contract["credential_mode"]}
            if contract.get("credential_mode")
            else {}
        ),
        "secrets": contract["secrets"],
        "variables": contract["variables"],
        **({"defaults": contract["defaults"]} if contract["defaults"] else {}),
    }


def resolve_effective_values(contract, organization_values, action_values=None):
    """Resolve non-secret provider variables without exposing values in diagnostics.

    Runtime values use the trusted source order defined by the provider contract.
    Job timeout is intentionally excluded: GitHub evaluates it before any action
    runs, so generated callers resolve its instance-configured default.
    """
    organization_values = organization_values or {}
    action_values = action_values or {}
    values = {}
    sources = {}
    required = set(contract["variables"]) - set(contract["optional_variables"])
    for logical in required:
        value = organization_values.get(logical, "")
        if not isinstance(value, str) or not value.strip():
            raise ProviderConfigError(f"required provider value is unresolved: {logical}")
        values[logical] = value
        sources[logical] = "organization variable"
    for logical in contract["optional_variables"]:
        if logical == "job_timeout_minutes":
            continue
        candidates = (
            (organization_values.get(logical), "organization variable"),
            (action_values.get(logical), "instance action"),
            (contract["defaults"].get(logical), "instance config"),
            (contract["template_defaults"].get(logical), "workflow default"),
        )
        for value, source in candidates:
            if isinstance(value, str) and value.strip():
                values[logical] = value
                sources[logical] = source
                break
        else:
            raise ProviderConfigError(f"optional provider value is unresolved: {logical}")
    return values, sources
