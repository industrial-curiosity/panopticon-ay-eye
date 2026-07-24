"""Validate and persist an instance's provider configuration without handling secret values."""

import argparse
import json
from pathlib import Path

from .config import ORG_CONFIG_BASENAME
from .providers import PROVIDERS, ProviderConfigError, provider_config


def configure(instance_root, provider, names, credential_mode=None):
    """Update only the LLM block in the instance configuration and return the effective block."""
    if provider not in PROVIDERS:
        raise ProviderConfigError(
            f"select a supported provider ({', '.join(PROVIDERS)}), not {provider!r}"
        )
    definition = PROVIDERS[provider]
    mode_definition = definition.get("credential_modes", {}).get(credential_mode or "github-oidc", {})
    allowed_names = {
        logical
        for provider_definition in PROVIDERS.values()
        for kind in ("secrets", "variables")
        for logical in provider_definition[kind]
    }
    allowed_names.update(
        logical
        for provider_definition in PROVIDERS.values()
        for mode in provider_definition.get("credential_modes", {}).values()
        for logical in mode.get("variables", {})
    )
    unknown_names = set(names) - allowed_names
    if unknown_names:
        raise ProviderConfigError(
            f"provider {provider!r} has unknown logical names: {sorted(unknown_names)}"
        )
    secrets = {
        key: names.get(key, default)
        for key, default in definition["secrets"].items()
    }
    variables = {
        key: names.get(key, default)
        for key, default in {**definition["variables"], **mode_definition.get("variables", {})}.items()
    }
    llm = provider_config(
        provider,
        secrets,
        variables,
        credential_mode if provider == "bedrock" else None,
    )

    path = Path(instance_root) / ORG_CONFIG_BASENAME
    document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(document, dict):
        raise ProviderConfigError(f"{ORG_CONFIG_BASENAME} must contain a JSON object")
    document["llm"] = llm
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return llm


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-root", default=".")
    parser.add_argument("--provider", required=True, choices=tuple(PROVIDERS))
    parser.add_argument("--credential-mode")
    logical_names = {
        logical: default
        for definition in PROVIDERS.values()
        for kind in ("secrets", "variables")
        for logical, default in definition[kind].items()
    }
    for logical, default in sorted(logical_names.items()):
        parser.add_argument(f"--{logical.replace('_', '-')}-name", default=default)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    names = {
        key.removesuffix("_name"): value
        for key, value in vars(args).items()
        if key.endswith("_name")
    }
    try:
        llm = configure(args.instance_root, args.provider, names, args.credential_mode)
    except (ProviderConfigError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(json.dumps(llm, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
