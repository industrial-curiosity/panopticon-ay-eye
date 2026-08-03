"""Resolve optional provider runtime values and publish only their source labels.

This module runs inside reusable provider workflows after the instance checkout.
It reads raw caller inputs and fixed-action outputs, writes resolved non-secret
runtime values to ``GITHUB_ENV``, and never writes those values to logs.
"""

import os
from pathlib import Path

from .config import load_org_config, provider_contract
from .providers import ProviderConfigError, resolve_effective_values


ENVIRONMENT_NAMES = {
    "model": "PANOPTICON_LLM_MODEL",
    "endpoint": "PANOPTICON_LLM_ENDPOINT",
    "aws_region": "PANOPTICON_AWS_REGION",
    "aws_role_arn": "PANOPTICON_AWS_ROLE_ARN",
    "timeout_seconds": "PANOPTICON_LLM_TIMEOUT_SECONDS",
    "max_attempts": "PANOPTICON_LLM_MAX_ATTEMPTS",
    "max_correction_attempts": "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS",
}
ACTION_ENVIRONMENT_NAMES = {
    "timeout_seconds": "PANOPTICON_ACTION_TIMEOUT_SECONDS",
    "max_attempts": "PANOPTICON_ACTION_MAX_ATTEMPTS",
    "max_correction_attempts": "PANOPTICON_ACTION_MAX_CORRECTION_ATTEMPTS",
}


def resolve_for_workflow(instance_root, environment):
    """Return resolved values and source labels from workflow environment data."""
    contract = provider_contract(load_org_config(instance_root))
    inputs = {
        logical: environment.get(name, "")
        for logical, name in ENVIRONMENT_NAMES.items()
        if logical in contract["variables"]
    }
    action_values = {
        logical: environment.get(name, "")
        for logical, name in ACTION_ENVIRONMENT_NAMES.items()
    }
    values, sources = resolve_effective_values(contract, inputs, action_values)
    sources["job_timeout_minutes"] = environment.get(
        "PANOPTICON_JOB_TIMEOUT_SOURCE", "workflow default"
    )
    return values, sources


def main(environment=None):
    """Write resolved runtime values and safe source labels for later workflow steps."""
    environment = environment if environment is not None else os.environ
    instance_root = Path(environment["PANOPTICON_INSTANCE_DIR"])
    try:
        values, sources = resolve_for_workflow(instance_root, environment)
    except ProviderConfigError as exc:
        reason = f"Panopticon provider configuration is unresolved: {exc}"
        with open(environment["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
            summary.write(f"## {reason}\n\n")
            summary.write(
                "Configure the named organization variable, instance default, or fixed "
                "default action, then rerun.\n"
            )
        print(f"::error::{reason}; see the step summary")
        return 1
    with open(environment["GITHUB_ENV"], "a", encoding="utf-8") as output:
        for logical, value in values.items():
            output.write(f"{ENVIRONMENT_NAMES[logical]}={value}\n")
    with open(environment["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write("## Panopticon effective provider configuration\n\n")
        for logical in sorted(sources):
            summary.write(f"- `{logical}`: {sources[logical]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
