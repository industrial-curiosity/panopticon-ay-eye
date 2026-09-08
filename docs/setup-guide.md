---
type: guide
---

# Org-owner setup guide

How to stand up Panopticon for an organization: create your private instance
from this template,
configure org secrets, tune gating, and initialize child repos.

## 1. Create the instance repo

GitHub does not allow private forks of public repositories, so the instance is
created from a
**template repository**:

1. On [this repo's GitHub
   page](https://github.com/industrial-curiosity/panopticon-ay-eye), click
   **Use this template → Create a new repository** and create a **private** repo
   in your org
   (e.g. `acme/panopticon-instance`). If the button is missing, a template-repo
   owner must first
   enable it at [**Settings → Template
   repository**](https://github.com/industrial-curiosity/panopticon-ay-eye/settings).
2. The instance repo is your org's knowledge base. It will accumulate:
   - `docs/{repo}/` — a copy of each child repo's generated documentation
   - `interfaces/{repo}.json` — one interface index shard per child repo
   - `interfaces/index.json` — the compiled org-wide index (with its `conflicts`
     array)
   - `panopticon.config.json` — org configuration (see step 3)
3. To pull template updates later, open **Actions → Sync from template → Run
   workflow** at
   `https://github.com/YOUR-ORG/YOUR-INSTANCE-REPO/actions/workflows/sync-from-template.yml`
   (replace `YOUR-ORG/YOUR-INSTANCE-REPO` with your instance). The small
   instance workflow calls the
   template's shared, caller-only sync workflow, so fixes to the sync logic take
   effect on the next run without
   copying another full workflow into your instance. The shared workflow is not
   directly runnable. If checkout,
   fetch, merge, validation, or push fails, the run summary names the failed
   stage and detected error before providing equivalent local recovery commands.
   Set the optional `template_ref` input to a named template branch when testing
   a template change; leave it blank to use `main`. The successful summary
   records the selected ref and every repository-relative path changed by the
   merge, or explicitly says that no paths changed.
   You can
   also enable the weekly schedule in the workflow file to receive updates
   automatically.

   Template sync preserves the instance version of every exact path in
   `protected_paths`, the protected
   `panopticon.diagram.config.json`, and an existing generated
   `docs/architecture.md`. Any other customized
   template-managed file follows normal Git merge behavior: a template-only
   change can update it, while a change
   on both sides can require local conflict resolution. Add any customization
   that must always win to
   `protected_paths` before syncing. This protection applies only to
   template-to-instance sync;
   `python3 -m panopticon.sync` in a child repository manages its own files and
   does not consult
   `protected_paths`.

   Sync uses GitHub's default token when the update does not change a workflow
   file. To sync changes under
   `.github/workflows/`, add `PANOPTICON_INSTANCE_TOKEN`: an organization or
   repository Actions secret
   containing a GitHub fine-grained PAT with Contents and Workflows read/write
   access to the instance repo.
   If it is missing, the workflow stops before pushing and shows these
   instructions in its step summary.

4. No tagging is required to get started — child caller workflows default to the
   instance repo's
   default branch until you opt into pinning a ref (see step 3's
   `workflow_ref`).

### One-time workflow update for existing instances

An existing instance has an older, full copy of `sync-from-template.yml`, which
cannot repair itself if it
breaks before pushing its own update. Replace it once from a local clone of the
instance repo with the fixed
shared-workflow caller:

```bash
gh api \
  repos/industrial-curiosity/panopticon-ay-eye/contents/.github/workflows/sync-from-template.yml \
  --jq '.content' | base64 --decode > .github/workflows/sync-from-template.yml

git add .github/workflows/sync-from-template.yml
git commit -m "fix: use the shared template sync workflow"
git push
```

Then run **Actions → Sync from template → Run workflow**. Instances created
after the updated workflow is
published inherit it automatically and do not need this one-time step. Keep this
caller fixed: it deliberately does not offer a repository or workflow path input,
so it cannot redirect privileged sync credentials. Its only dispatch input selects
a ref within the fixed Panopticon template repository.

## 2. Configure the instance LLM provider

The template deliberately starts with no LLM provider selected. In the instance
repo:

1. Choose exactly one provider workflow:
   - **Actions → Configure Panopticon — LiteLLM
     (<https://github.com/YOUR-ORG/YOUR-INSTANCE-REPO/actions/workflows/configure-panopticon-litellm.yml>)**
   - **Actions → Configure Panopticon — OpenAI
     (<https://github.com/YOUR-ORG/YOUR-INSTANCE-REPO/actions/workflows/configure-panopticon-openai.yml>)**
   - **Actions → Configure Panopticon — Bedrock
     (<https://github.com/YOUR-ORG/YOUR-INSTANCE-REPO/actions/workflows/configure-panopticon-bedrock.yml>)**

   Replace `YOUR-ORG/YOUR-INSTANCE-REPO` with your instance, for example
   `acme/panopticon-instance`.

2. Select **Run workflow** and choose the instance's default branch. The
   workflow fixes the provider
   identity and displays only that provider's configuration fields.
   **Configure Panopticon — OpenAI** always uses
   `https://api.openai.com/v1`; it does not accept an endpoint variable or
   override.
3. If you chose Bedrock, select the credential path that matches your
   organization:
   - **github-oidc** (the default) has Panopticon assume an IAM role directly.
     It requires the
     AWS region and IAM role ARN organization variables described below.
   - **instance-managed** uses the fixed, reviewed instance action at
     `.github/actions/panopticon-aws-credentials/action.yml`. Choose it when
     your organization
     already centralizes AWS authentication in an instance-local action (for
     example, a wrapper
     around its own credentials action). This path does not require either AWS
     variable.
4. Review the organization secret and variable *names*. Keep the documented
   defaults or enter
   your organization's names. Never enter credential values in these fields:
   - **Instance checkout token secret** is the name of the organization secret
     holding the GitHub
     fine-grained PAT that child workflows use to check out the private instance
     repo. Leave
     `PANOPTICON_INSTANCE_TOKEN` unless your organization uses another secret
     name.
   - **Model variable** is the name of the organization variable, not the model
     identifier itself.
     With the default `PANOPTICON_LLM_MODEL`, set its value to a LiteLLM or
     OpenAI model such as `gpt-4o-mini`, or to the selected Bedrock model's Converse-compatible
     identifier.
   - **AWS region variable** and **AWS IAM role ARN variable** are names, not
     AWS values. In
     `github-oidc` mode their respective values can be `us-east-1` and
     `arn:aws:iam::123456789012:role/panopticon-bedrock`; both are ignored in
     `instance-managed` mode.
5. Select **Run workflow** and wait for a green completed run that commits
   `panopticon.config.json`.

The equivalent CLI commands are below. Run exactly one, replacing
`YOUR-ORG/YOUR-INSTANCE-REPO` with your instance; for example,
`acme/panopticon-instance`.

```bash
gh workflow run configure-panopticon-litellm.yml --repo YOUR-ORG/YOUR-INSTANCE-REPO --ref main
gh workflow run configure-panopticon-openai.yml --repo YOUR-ORG/YOUR-INSTANCE-REPO --ref main
gh workflow run configure-panopticon-bedrock.yml --repo YOUR-ORG/YOUR-INSTANCE-REPO --ref main
gh run watch --repo YOUR-ORG/YOUR-INSTANCE-REPO
```

For Bedrock with `github-oidc`, grant the named IAM role `bedrock:InvokeModel`
access to the
configured model and trust GitHub's OIDC identity for the child repositories.
With
`instance-managed`, implement the fixed action named above so it obtains
credentials and writes
`PANOPTICON_AWS_REGION` (for example `us-east-1`) to `$GITHUB_ENV`. For LiteLLM,
configure the
endpoint and API key.

### Bedrock GitHub OIDC checklist

1. In AWS IAM, add the GitHub OIDC provider URL
   `https://token.actions.githubusercontent.com` with
   audience `sts.amazonaws.com`; follow GitHub's
   [AWS OIDC
   guide](https://docs.github.com/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).
2. Create a role whose trust policy restricts
   `token.actions.githubusercontent.com:sub` to the intended
   child repositories. Copy the subject format from GitHub's current OIDC
   reference rather than guessing it.
3. Grant that role `bedrock:InvokeModel` on the selected model or
   inference-profile resources. For an application inference profile, grant
   `bedrock:InvokeModel` on both the selected profile ARN and its underlying
   foundation-model ARN. Converse uses that permission; retain
   `bedrock:GetInferenceProfile` separately when the integration discovers or
   reads profile metadata. See AWS's
   [Bedrock inference
   prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.html).
4. Put the role ARN and region into the organization variables named by
   **Configure Panopticon — Bedrock**, and use a model identifier documented as
   Converse-compatible.
   No long-lived AWS access-key secret is required.

### Bedrock instance-managed credential action checklist

1. Copy the reviewed [credential-action example](examples/panopticon-aws-credentials/action.yml)
   to `.github/actions/panopticon-aws-credentials/action.yml`. This fixed path
   is deliberate: child repositories cannot select an arbitrary action.
2. Replace only the example's organization broker step with the approved
   organization mechanism. The action runs for the child caller identity and
   accepts no credential value through Panopticon configuration.
3. Have the action write the selected region to `$GITHUB_ENV` as
   `PANOPTICON_AWS_REGION` and preserve the example's `aws_region` output
   contract. Verify that output before committing the action.
4. Select `instance-managed` in **Configure Panopticon — Bedrock**. Do not
   create
   `PANOPTICON_AWS_REGION` or `PANOPTICON_AWS_ROLE_ARN` solely for Panopticon in
   this mode.

When the trusted provider contract selects Bedrock `instance-managed`, template
sync automatically protects the fixed credential-action path with the runtime
`merge.ours` driver. Add that path to `protected_paths` only when documenting a
separate custom instance file.

For an existing instance, sync the template to replace the generic configuration
workflow with all three provider-specific entrypoints. An already configured
instance does not need to rerun configuration or child bootstrap solely because
of this workflow split. If you change the provider, credential mode, or
configured names, run the matching configuration workflow and then rerun
bootstrap in every child. Review, commit, and push each generated caller change
before removing old secret names or workflow versions. If the instance-token
secret name changes, keep the old secret available until every child caller has
been regenerated; removing it early can prevent instance checkout before the
workflow can diagnose a stale caller-compatibility revision. Runtime-only
provider behavior changes, such as adding an optional effective-value source,
do not require child bootstrap.

### Four-gate rollout and troubleshooting

Treat the first child run as four ordered gates. Record the last gate that has
green evidence; a green gate proves only that the run reached the next boundary.
Read the run-page banner before opening job logs. A zero-job **workflow file
issue** can mean that the private instance does not permit the child to call its
workflow, not that the YAML is missing or invalid.

| Gate | Observable symptom | Authoritative evidence | Owner and scope | Runtime guidance | Proof before advancing |
| --- | --- | --- | --- | --- | --- |
| 1. Reusable-workflow access | Zero jobs, `workflow was not found`, or an access/parse banner before any job starts | The run-page banner; the instance Actions access API; then the selected workflow contents API at the configured ref | Instance administrator; normally instance-wide for the allowed organization, with a separate child repository check | Follow the access failure's emitted guidance; do not edit YAML until the access check establishes the gate state. | The access endpoint reports an allowed level and the contents lookup returns the selected workflow path at the configured ref. |
| 2. Effective provider configuration | `missing ... configuration`, missing default, invalid configured name, or stale caller-compatibility revision | The completed provider-configuration workflow, committed `panopticon.config.json`, generated caller's contract comments, and the `Resolve effective provider values` step summary | Instance owner for names/defaults; child owner when its caller is stale | Follow the provider workflow or bootstrap summary for the affected boundary. | The configuration run is green, the caller-compatibility revision matches the instance or its accepted legacy revision, and effective values resolve before provider preflight without exposing values. |
| 3. Caller-repository identity and credentials | `id-token` permission errors, OIDC trust denial, `AssumeRoleWithWebIdentity` errors, missing credentials, or a credential wrapper timeout | The credential-step outcome and summary, the child caller's `permissions` block, and `aws sts get-caller-identity` from the caller job | Per child for identity registration and trust; instance owner for the fixed credential action and its configured names | Follow the caller-owned gate-3 summary, which remains available after credential failure or timeout. | The credential step and caller identity check succeed, and the summary identifies the child caller before provider preflight. |
| 4. Real provider-request compatibility | Credentials and preflight pass, then a real structured request fails with a model, request-shape, unsupported-control, or provider API error | The provider request error and the exact selected model/request shape; never infer this gate from credentials-only preflight | Provider adapter/model owner, with the instance owner responsible for the configured model name | Follow the provider-request failure output and preserve the smallest supported request shape. | One real structured inference completes with the rollout model; capability preflight alone is not sufficient proof. |

#### Pre-child private-workflow access check

Before writing child files, authenticate as an instance administrator with a
fine-grained token that has `Administration: Read` and `Contents: Read` on the
instance repository, or use a classic PAT with `repo` scope. Replace the
placeholders; do not copy credential values into the command:

```bash
INSTANCE='YOUR-ORG/YOUR-INSTANCE-REPO'
WORKFLOW_REF='main'
PROVIDER='bedrock'  # one of: litellm, openai, bedrock

gh api "repos/${INSTANCE}/actions/permissions/access" \
  --jq '.access_level'
gh api "repos/${INSTANCE}/contents/.github/workflows/panopticon-pr-${PROVIDER}.yml?ref=${WORKFLOW_REF}" \
  --jq '.path'
```

The matching UI is
`https://github.com/YOUR-ORG/YOUR-INSTANCE-REPO/settings/actions`. The access
response must allow the intended organization or enterprise callers before the
contents lookup is meaningful. If the access request returns HTTP 403,
reauthenticate with `Administration: Read` on the instance repository; a 403 is
an authentication failure, not an access-policy result. If the first call
reports `none`, the instance owner fixes the policy; do not treat the child's
zero-job banner as evidence that the called workflow is absent. If access is
allowed but the contents call fails, confirm `Contents: Read`, inspect the
exact ref and path, and then run the workflow-contract validator against the
instance copy.

If the read-only check reports `none`, an instance administrator can apply the
policy mutation below. It changes the instance's reusable-workflow access
policy and requires an administrator token with the documented administration
permission; it is not an automated Panopticon step:

```bash
gh api -X PUT repos/YOUR-ORG/YOUR-INSTANCE-REPO/actions/permissions/access -f access_level=organization
```

Operators who only have read access can use the read-only check and the
Settings UI path above instead.

The generated caller runs in the child repository's security context. Reusable
workflow code does not transfer repository identity: for GitHub OIDC, the
subject identifies the child caller, while the reusable workflow location is a
separate claim. Organizations using per-repository roles or credential wrappers
must therefore provision every child separately; the instance's own role is not
a substitute.

When a credential step fails or times out, use the caller-owned gate-3 summary
as the source of recovery instructions. The workflow places that output after
the credential boundary so it remains available when the composite action is
cancelled.

Gate 4 needs one real structured request. A green `Provider preflight` step
proves credentials and capability only; it does not prove that the selected
model accepts every request field. Keep provider-request failures with the
adapter/model owner and preserve the smallest supported request shape.

### 2.1 Configure org-level secrets and variables

Go to your org's **Settings → Secrets and variables → Actions
(<https://github.com/organizations/YOUR-ORG/settings/secrets/actions>)**
(replace `YOUR-ORG` with your GitHub org slug).

For each secret and variable below, set **Repository access → Selected
repositories** and add:

- the **instance repo** (created in step 1), and
- every **child repo** Panopticon should cover.

Make sure that your token is visible to your instance repository as well as your
child repositories.

The instance repo needs access because the Sync from template workflow runs
there.
Child repos never configure per-repo secrets or variables. Bootstrap generates
thin callers that
explicitly map these instance-selected organization names to canonical provider
workflow inputs.

**Secrets** (encrypted; never visible in logs):

| Secret | What it is |
| --- | --- |
| `PANOPTICON_LLM_API_KEY` *(LiteLLM or OpenAI)* | Bearer token for the LiteLLM endpoint or OpenAI Platform API |
| `PANOPTICON_INSTANCE_TOKEN` | Fine-grained PAT scoped to the instance repo — [see instructions below](#creating-panopticon_instance_token) |

**Variables** (plaintext; visible in logs):

| Variable | What it is |
| --- | --- |
| `PANOPTICON_LLM_ENDPOINT` *(LiteLLM)* | LiteLLM-compatible endpoint |
| `PANOPTICON_AWS_REGION` *(Bedrock github-oidc only)* | AWS region containing the Bedrock model, for example `us-east-1` |
| `PANOPTICON_AWS_ROLE_ARN` *(Bedrock github-oidc only)* | IAM role ARN that child PR workflows assume through GitHub OIDC, for example `arn:aws:iam::123456789012:role/panopticon-bedrock` |
| `PANOPTICON_LLM_MODEL` | LiteLLM or OpenAI model name (for example, `gpt-4o-mini`) or Bedrock Converse-compatible model identifier |

Request timeout and retry-budget variables are optional. See [provider
configuration defaults](provider-configuration.md) for their source precedence,
the configuration-workflow default fields, and the fixed instance Action path.

These are consumed only by the shared CI workflows. Local flows —
initialization, doc generation,
index updates — run in each developer's own AI agent harness and need none of
them.

### Creating PANOPTICON_INSTANCE_TOKEN

1. Go to [**New fine-grained personal access
   token**](https://github.com/settings/personal-access-tokens/new).
2. Set **Resource owner** to your org (e.g. `acme`).
3. Under **Repository access**, choose **Only select repositories** and add your
   **instance repo**
   — the private repo you created in step 1 (e.g. `acme/panopticon-instance`).
   This is not a child
   repo; it is the central knowledge-base repo that all child repos push into.
4. Under **Permissions → Repository permissions**, add:
   - **Contents** → Read and write
   - **Issues** → Read and write
   - **Workflows** → Read and write *(required to push `.github/workflows/`
     files during sync)*
   - *(Metadata → Read-only is added automatically by GitHub)*
5. Set an expiration, click **Generate token**, and copy it immediately.
6. Add the copied token as the `PANOPTICON_INSTANCE_TOKEN` org secret at
   **Settings → Secrets and variables → Actions
   (<https://github.com/organizations/YOUR-ORG/settings/secrets/actions>)**.

## 3. Org configuration

### Generated complex-organization overlay

Organizations with centralized credential brokering, custom workflow access,
or per-child identity provisioning can start from the deterministic profile
workflow. It keeps provider paths and runtime trust in the template registry:

```bash
python3 -m panopticon.organization_template validate PROFILE
python3 -m panopticon.organization_template generate PROFILE --instance-root INSTANCE --output OVERLAY
python3 -m panopticon.organization_template apply OVERLAY --instance-root INSTANCE --check
python3 -m panopticon.organization_template apply OVERLAY --instance-root INSTANCE
```

Review the manifest and generated checklists before applying. The overlay
contains separate instance-wide and child onboarding guidance in four-gate
order. Apply writes only manifest-declared files; to roll back before commit,
discard the overlay. After commit, restore the previous reviewed instance files
through the normal instance change process. See the [complex-organization
template reference](complex-organization-template.md) for the complete field
reference and security rules.

`panopticon.config.json` at the instance repo root:

```json
{
  "schema_version": 1,
  "gating": {
    "init": "blocking",
    "doc-drift": "blocking",
    "interface-conflict": "advisory",
    "diagram-missing": "advisory"
  },
  "protected_paths": [".agents/skills/panopticon-doc-generation/references/custom.md"],
  "internal_registries": ["packages.example.com"]
}
```

- **`gating`** — per-check outcomes. Defaults: initialization and doc-drift
  checks **fail** the
  workflow when they find a problem; interface-conflict checks are **advisory**
  (reported but
  passing) because LLM-extracted entries can false-positive; diagram-missing
  checks are
  **advisory** at first so already-initialized repos aren't immediately blocked
  before they've
  regenerated docs to pick up the new `## Architecture diagram` section — flip
  it to `blocking`
  once your repos have backfilled. Each check type can be moved in either
  direction.
- **`workflow_ref`** *(optional)* — the git ref (tag or branch) at which the
  init tooling wires child
  caller workflows to the instance's reusable workflows. Omit it and the
  instance repo's default branch
  is used — no tagging required to get started. Set it once you want to pin
  caller workflows to a
  specific tag or branch instead.

### Child-level conflict override

The instance configuration supplies the default interface-conflict policy. A
child repository can explicitly override that default in its committed
`panopticon/config.json`:

```json
{
  "gating": {
    "interface-conflict": "blocking"
  }
}
```

Only `advisory` and `blocking` are accepted. The child override takes
precedence over the instance value; when it is absent, the instance value (or
the built-in advisory default) applies. Both modes produce a prominent warning
in the PR report, while only `blocking` fails the interface-conflict check.

### Naming migration and PR review

When an existing child repository has generic local names, run the
`panopticon-doc-generation` skill locally. It loads the instance's compiled
interface index, compares the code and configuration evidence, writes reviewed
`panopticon-interface` hints where needed, regenerates the local index, and
re-renders the interface documentation. Review and commit those hints and
shard changes in controlled child pull requests. Each PR's maintained Panopticon
report shows bounded possible matches, the deterministic prospective merge, the
effective conflict policy, and the child Mermaid architecture diagram. Candidate
matches are advisory; exact simulation conflicts use the configured advisory or
blocking outcome.

- **`protected_paths`** *(optional, default `[]`)* — literal paths (skills,
  vendored tooling modules,
  or other instance-repo content) your org has customized at the instance level,
  which
  `sync-from-template` must never overwrite. Unlike
  `panopticon.diagram.config.json`'s protection
  (a template-declared, fixed registry), these are org-declared and open-ended —
  list any exact file
  path you've customized. Protection is applied via `.git/info/attributes` on
  every sync run (never
  a commit, never the tracked `.gitattributes`), so it's invisible in the
  tracked tree; each sync run's
  GitHub Actions step summary lists which paths were protected that run as the
  audit trail. Entries
  are exact file paths, not directory globs — list each customized file
  individually.

#### Protected-path debt register

Treat every `protected_paths` entry as temporary maintenance debt. Add one row
to this register for each exact path and update it after every template sync:

| Exact path | Reason for protection | Owner | Upstream issue/change that replaces it | Last reconciliation result | Removal condition |
| --- | --- | --- | --- | --- | --- |
| `<exact-template-path>` | `<why the instance customization is required>` | `<team or role>` | `<public issue, change, or design reference>` | `<YYYY-MM-DD: result and follow-up>` | `<specific condition for deleting the path>` |

The register is review metadata, not a replacement for the JSON list. Keep
credential values, account IDs, and private links out of both the public
template and any contribution copied upstream. Remove a path only after the
upstream replacement is present, reconciled, and proven by the relevant child
run.

- **`internal_registries`** *(optional, default `[]`)* — host or URL substrings
  identifying your org's
  own private package registry/registries (e.g. an Artifactory or Nexus host).
  Dependency-indexing uses
  this to recognize that a repo's dependency resolves from your org's own
  infrastructure rather than a
  third-party one — the same field covers both a consumer repo installing an
  internal package and a
  producer repo publishing one, so you configure your registry identity once,
  not per ecosystem.
  Ecosystems whose dependency declarations already embed your org's identity
  (e.g. Go module paths
  under your org's GitHub organization) need no entry here at all. When a
  dependency or interface
  can't be resolved automatically, developers pin it with a hint comment — see
  `docs/hint-reference.md` for every hint form and exactly how each one behaves.

### Optional feature configuration

Instance maintainers can enable template-owned optional capabilities from the
[Configure Panopticon — Features workflow](https://github.com/YOUR-ORG/YOUR-INSTANCE-REPO/actions/workflows/configure-panopticon-features.yml).
Replace `YOUR-ORG` and `YOUR-INSTANCE-REPO` with the organization and private
instance repository before opening the link.

Select a registered feature and one of these modes:

- `disabled` — do not install the feature or run its checks.
- `advisory` — install it and report findings while migrating existing child
  documentation.
- `blocking` — install it and fail initialization or PR gating on findings.

For the initial OKF rollout, select `okf` with `advisory`, bootstrap or sync
the child repositories, run the installed documentation-generation guidance,
review the generated Markdown, and commit the migration. Select `blocking`
after the child bundles validate cleanly. Selecting `disabled` stops new
selection and offers cleanup during interactive bootstrap; non-interactive
bootstrap and `python3 -m panopticon.sync` remove only paths recorded in the
managed feature receipt and never commit those deletions.

## 4. Initialize a child repo

Initialization has three phases: a deterministic bootstrap, an AI agent pass,
and a final validation step.

### Phase 1 — Bootstrap (from the child repo, no AI needed)

Run the public template launcher from inside the child repo. The same command
supports public and private
instance repositories:

```bash
cd my-service
curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | PANOPTICON_INSTANCE='YOUR-ORG/YOUR-INSTANCE-REPO' python3
```

The launcher asks for any missing interactive inputs and then runs that instance
repository's own installer. Authenticate every install, including a public
instance, with `GH_TOKEN`, `GITHUB_TOKEN`, or an existing `gh auth` session:
authenticated requests have a much higher GitHub API quota. Private instances
require authentication. Supply a token through your shell or CI secret
environment; never put its value directly in the launcher command. The launcher
stops before writing
if the provider is unconfigured or invalid. Failure-specific recovery appears
in the bootstrap output when needed. Optional inputs are:

```bash
export PANOPTICON_SKILLS_LOCATION=.agents/skills
# Optional: select a branch, tag, or commit instead of the instance's default branch.
export PANOPTICON_INSTANCE_REF=YOUR-INSTANCE-REF
```

For example, use `PANOPTICON_INSTANCE_REF=release-2026-07`. The instance
installer chooses where skills live (template default
`.agents/skills/`; see
[`docs/agentskills-support.md`](agentskills-support.md)). Set
`PANOPTICON_SKILLS_LOCATION` to skip that
prompt for non-interactive or CI runs.

Once a location is chosen, the script will:

- Install the Panopticon skills there
- Download the selected instance's versioned, data-only local-tooling manifest
  and vendor its listed subset of the `panopticon` Python package into
  `panopticon/`, so the
  `python3 -m panopticon...` commands the skills use in Phase 2 work immediately
  — no need to clone the
  instance repo or set up a Python environment yourself
- Download `PANOPTICON.md` to the repo root — a concise getting-started guide
  (how the system works,
  where architecture diagrams live, and how to keep this repo's skills/tooling
  current)
- Wire the four caller GitHub Actions workflows into `.github/workflows/`
- Check that org secrets and variables are configured (report-only — nothing is
  blocked)
- Print a reminder of `PANOPTICON.md` and the `python3 -m panopticon.sync`
  command (every run, not
  just the first), then the one prompt to give your AI agent in Phase 2

### Phase 2 — Agent (follow the printed prompt)

Give your AI agent (Claude Code, Cursor, or whichever tool you configured) the
printed prompt — a single
skill that sequences interface indexing, dependency indexing, documentation
generation, and finalization
on its own, with a resumable checkpoint if your agent session gets interrupted
partway through. Each of
the underlying skills also works standalone if you'd rather run a step by
itself.

No `PANOPTICON_LLM_*` secrets or variables are needed locally — the agent uses
its own harness.

There is no manual handoff between documentation generation and finalization.
Before finalization creates `panopticon/config.json`, documentation generation
derives the repository, instance, and workflow reference from the caller
workflow written during bootstrap. If that workflow is missing or malformed,
the bootstrap or initialization output identifies the next action; otherwise
the initialization skill continues through finalization in the same run.

### Phase 3 — Finalize

The final prompt from the bootstrap output will instruct your agent to run the
finalization step,
which validates the agent-produced docs and index and writes
`panopticon/config.json` — the
initialization flag — only once validation passes. Every finalization attempt
also writes `panopticon-initialization-report.md` in the child repository root.
Read that report first if initialization is blocked: it identifies the affected
path or configuration and assigns it to the child repository, organization
configuration, or template/tooling. Follow the failure-specific next action
shown by the report.

### Commit and push

Commit and push everything the process created — the bootstrap script's own
final prompt gives the exact
command, since which paths that covers depends on the skills location you chose.

If initialization found and fixed documentation that contradicted the current
code, it records what it
changed and why in `panopticon-changelog.md` in your docs location, instead of
annotating the fix inline in
the docs themselves. Panopticon never stages or commits this file automatically
— review it and decide
whether to keep, edit, or discard it before you commit.

## 5. What runs afterwards

- **Every PR:** initialization check, doc-drift check (now also judging the `##
  Architecture
  diagram` section's staleness alongside prose), index-currency check, a
  deterministic
  diagram-existence check (the section exists and parses — no LLM call,
  independent of doc-drift's
  accuracy judgment), pre-merge conflict simulation against the compiled index
  (results as a PR comment), bounded AI comparison of likely child/instance
  interface matches, and a maintained PR comment containing the prospective
  Mermaid architecture diagram, a push of the PR's docs/index state to the `{repo}/{branch}` branch
  of the
  instance repo, and a **tooling-currency check** (see below) — always advisory,
  never affects the
  workflow's pass/fail outcome.
- **Every merge to main:** docs copied to `docs/{repo}/`, shard replaced,
  compiled index rebuilt,
  and the org-wide architecture diagram (`docs/architecture.md` in the instance
  repo — one section
  per repository with an interface or external dependency, a relationship diagram, and a table)
  rebuilt from the fresh
  compiled index, all pushed directly to the instance repo in the same commit;
  conflict issues
  opened/updated in both repos when the merge produces conflicts.
- **Every PR close:** the matching `{repo}/{branch}` instance branch is deleted.

Diagram rendering format defaults to Mermaid and is configurable per instance
via
`panopticon.diagram.config.json` at the instance repo root — this file is
protected from
`sync-from-template`'s merge (your customization always wins), and syncing warns
(non-blocking) if
the template adds or removes a config field you haven't picked up.

The generated `docs/architecture.md` follows a different rule: it is not
protected configuration and does
not belong in `protected_paths`. The template sync workflow declares it as
instance-owned generated output
and preserves the instance copy whenever both sides contain or change the path.

## 6. Keeping a child repo's skills and tooling current

Every child repo gets a `PANOPTICON.md` at its root from the bootstrap script
(Phase 1) — a concise
version of this section, so a maintainer working in that repo doesn't need this
setup guide open to
remember how to stay current. The bootstrap script also reprints the sync
command below on every
run, first bootstrap and re-run alike.

A child repo's downloaded skills, vendored `panopticon/` tooling, and wired
workflow ref are all
snapshots taken at bootstrap time. Nothing forces them to stay current — the
**tooling-currency
check** (every PR, see above) warns, non-blocking, when any of the three has
drifted from the
instance repo's current default branch: the wired ref no longer resolves to the
instance's tip
commit, or a skill/tooling file's content differs, is missing, or is extra. It's
always advisory
and never gated — acting on it is entirely at your discretion.

The check and local sync also identify unmanaged Python modules under
`panopticon/`. An **instance-excluded** warning means the selected instance
contains the module but its versioned data-only local-tooling manifest excludes
it (for example, a CI-only runtime module). A **child-only and unknown** warning
means the module is absent from the selected instance. Neither warning deletes
or changes the file. A malformed manifest is an actionable bootstrap or sync
error, but only a non-blocking tooling-currency warning.

To pull the instance's current skills and tooling into an already-bootstrapped
child repo:

```bash
python3 -m panopticon.sync
```

Or, for a reviewable update, run **Actions → Panopticon resource sync → Run
workflow** from the child repository's default branch. It creates or updates one
open pull request containing the managed resource changes. After that pull
request is merged or closed, the next changed sync creates a new pull request;
when resources are current, it creates no pull request.

This overwrites the repo's skills and vendored `panopticon/` tooling
unconditionally — there is no
per-file protection at the child layer. Review `git diff`/`git status` before
committing; anything
you disagree with, don't commit or hand-edit back. To see what would change
without writing
anything:

```bash
python3 -m panopticon.sync --check-updates
```

For each warning, review the module's owner and imports before acting. Keep
child-owned modules that are still needed. For an unwanted legacy or CI-only
module, remove it only in a separate, reviewed change, run the child test suite,
and commit that removal separately from the tooling refresh.

If you've customized a skill or tooling module at the **instance** level, use
the protected-path debt register in step 3. That list protects the instance
copy from template sync only; child `python3 -m panopticon.sync` deliberately
overwrites its managed resources and does not consult it.

## 7. Finding the org-wide architecture diagram from a child repo

A child repo's `README.md` links to its local architecture document and the org
architecture diagram. Links within the child documentation tree are relative, so
they work in both the child repo and its mirrored instance documentation. Links
to the org diagram are direct GitHub URLs, so they work immediately from either
location.

To print the org diagram URL for the current child repository, run:

```bash
python3 -m panopticon.org_diagram_link
```

The command prints one URL, such as
`https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a`.
