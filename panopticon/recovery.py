"""Shared, copy/paste-safe recovery text for provider configuration failures."""

PUBLIC_INSTALLER_URL = (
    "https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py"
)


def child_bootstrap_command(instance):
    """Return the exact installer command for a child bound to ``instance``."""
    return f"curl -fsSL {PUBLIC_INSTALLER_URL} | PANOPTICON_INSTANCE='{instance}' python3"


def configuration_recovery(instance, branch):
    """Return terminal-friendly recovery for an unconfigured instance."""
    workflow_url = f"https://github.com/{instance}/actions/workflows"
    litellm_url = f"{workflow_url}/configure-panopticon-litellm.yml"
    bedrock_url = f"{workflow_url}/configure-panopticon-bedrock.yml"
    return f"""Configure the Panopticon instance before bootstrapping a child repository.

GitHub Actions console (choose exactly one provider):
  LiteLLM: {litellm_url}
  Bedrock: {bedrock_url}
  1. Open the workflow for the provider the instance will use.
  2. Select Run workflow.
  3. Select branch {branch}.
  4. Review the secret and variable name fields; enter names only, never values.
  5. Select Run workflow and wait for the green completed run that commits panopticon.config.json.

Equivalent GitHub CLI commands (run exactly one):
  gh workflow run configure-panopticon-litellm.yml --repo {instance} --ref {branch}
  gh workflow run configure-panopticon-bedrock.yml --repo {instance} --ref {branch}
  gh run watch --repo {instance}

Then rerun child bootstrap from inside the child repository clone:
  {child_bootstrap_command(instance)}
"""


def missing_provider_recovery(instance, provider, missing):
    """Return a step-summary section for missing provider inputs."""
    lines = [f"## Panopticon: missing {provider} configuration", ""]
    lines.extend(f"- `{configured_name}` ({logical})" for logical, configured_name in missing)
    lines.extend(
        [
            "",
            "The instance configuration or child caller is stale. From inside the child clone run:",
            "",
            "~~~bash",
            child_bootstrap_command(instance),
            "~~~",
            "",
            "Review and commit the generated changes, push them, then rerun or await this PR workflow.",
            "",
        ]
    )
    return "\n".join(lines)


def stale_caller_recovery(instance):
    """Return a step-summary section for a caller with a stale configuration revision."""
    return "\n".join(
        [
            "## Panopticon child caller is stale",
            "",
            "Run this from inside the child clone:",
            "",
            "~~~bash",
            child_bootstrap_command(instance),
            "~~~",
            "",
            "Review and commit the generated changes, push them, then rerun or await this PR workflow. "
            "Keep old secret names available until regeneration finishes.",
            "",
        ]
    )
