# Provider Configuration Defaults

Use this guide after selecting LiteLLM, OpenAI, or Bedrock for an instance.
It explains which organization values are required, when an optional request
budget can use a default, and how to verify the result without exposing a
credential value.

## Choose a source for each value

Configure required values as organization Actions secrets or variables. Use the
provider-specific **Configure Panopticon** workflow to record their *names* in
`panopticon.config.json`; never enter a credential value in a workflow form or
config file.

| Value | Required | Organization source | Fallback source | Next action |
| --- | --- | --- | --- | --- |
| Instance token | Yes | Secret | None | Create `PANOPTICON_INSTANCE_TOKEN` (or the selected name) with instance-repository access. |
| LiteLLM/OpenAI API key | Yes | Secret | None | Create the selected API-key secret. |
| Model | Yes | Variable | None | Create the selected model variable. |
| LiteLLM endpoint | Yes for LiteLLM | Variable | None | Create the selected endpoint variable. |
| Bedrock region and role ARN | Yes for `github-oidc` | Variables | None | Create both selected variables; `instance-managed` does not use them. |
| Request timeout and retry budgets | No | Variable | Instance default, fixed action, then workflow default | Leave unset for the documented workflow defaults, or select a controlled fallback below. |
| PR job timeout | No | Variable | Instance default embedded in the caller, then workflow default | Use an instance default when the organization needs a shared timeout. |

An explicit non-empty organization variable always wins. Runtime request budgets
then use the fixed instance Action, an instance-configured default, and the
template workflow default. Job timeout cannot use the Action because GitHub
chooses the job timeout before any Action runs.

## Simplest setup: organization values and workflow defaults

1. Open the instance's **Configure Panopticon — LiteLLM**, **OpenAI**, or
   **Bedrock** workflow and choose the instance default branch.
2. Enter Actions *names* for required secrets and variables. Leave each
   `*_default` field empty to use the documented request-budget defaults.
3. Run the workflow and wait for it to commit `panopticon.config.json`.
4. In a child repository, rerun bootstrap:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='YOUR-ORG/YOUR-INSTANCE' python3
   ```

5. Review and commit the regenerated caller. Its initialization report names
   required missing organization settings separately from optional values
   supplied by a default.

## Instance-configured defaults

Each provider configuration workflow has optional non-secret fields for request
timeout, transport attempts, correction attempts, and job timeout. Enter a
value only when the organization needs a stable shared fallback. A changed value
changes the provider contract revision, so every child caller must be regenerated
with the bootstrap command above.

Use this path for a stable numeric policy. Do not use it for credentials, API
keys, tokens, model identity, LiteLLM endpoints, or Bedrock identity settings;
those remain required organization settings.

## Fixed instance Action for runtime defaults

Use `.github/actions/panopticon-provider-defaults/action.yml` only when a
runtime request budget must be computed or sourced by the instance. The Action
has exactly these optional outputs:

- `timeout_seconds`
- `max_attempts`
- `max_correction_attempts`

It runs after the reusable workflow checks out the instance and before provider
preflight. It cannot supply job timeout and must never output credentials or
secret values. Keep its path and output names unchanged; child configuration
cannot select another Action.

From the instance repository, validate the fixed workflow wiring before
pushing the Action change:

```bash
python3 -m unittest tests.test_provider_workflows -v
```

After changing the Action, open a test pull request and check the **Panopticon
effective provider configuration** section of the workflow summary. It should
list `instance action` for each output the Action supplied, without showing its
value. If the summary is unresolved, return an empty output to use the instance
configuration or workflow fallback, or correct the Action output name. Then
rerun the failed workflow.

For every instance configuration or Action change, regenerate callers from each
child repository and commit the result:

```bash
curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='YOUR-ORG/YOUR-INSTANCE' python3
```

## Verify and recover

Run child bootstrap after any contract change, then inspect
`panopticon-initialization-report.md`. The report and PR workflow summary show
only logical names and source labels such as `organization variable`, `instance
action`, `instance config`, or `workflow default`.

If a required value is missing, create the named organization setting and rerun
bootstrap. If an optional runtime value is unresolved, correct the named fixed
Action or instance default and rerun the provider workflow. If the summary says
the caller is stale, rerun bootstrap, review and commit the generated workflow,
then rerun the pull request checks.
