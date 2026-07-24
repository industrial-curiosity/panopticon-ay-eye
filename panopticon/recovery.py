"""Shared, copy/paste-safe recovery text for provider configuration failures."""

PUBLIC_INSTALLER_URL = (
    "https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py"
)


def child_bootstrap_command(instance):
    """Return the exact installer command for a child bound to ``instance``."""
    return f"curl -fsSL {PUBLIC_INSTALLER_URL} | PANOPTICON_INSTANCE='{instance}' python3"


def configuration_recovery(instance, branch):
    """Return terminal-friendly recovery for an unconfigured instance."""
    actions_url = f"https://github.com/{instance}/actions/workflows/configure-panopticon.yml"
    return f"""Configure the Panopticon instance before bootstrapping a child repository.

GitHub Actions console:
  1. Open {actions_url}
  2. Select Run workflow.
  3. Select branch {branch}.
  4. Replace select-a-provider with litellm or bedrock.
  5. Review the secret and variable name fields; enter names only, never values.
  6. Select Run workflow and wait for the green completed run that commits panopticon.config.json.

Equivalent GitHub CLI command (example selects LiteLLM with documented default names):
  gh workflow run configure-panopticon.yml --repo {instance} --ref {branch} -f provider=litellm
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
