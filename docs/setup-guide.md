# Org-owner setup guide

How to stand up Panopticon for an organization: create your private instance from this template,
configure org secrets, tune gating, and initialize child repos.

## 1. Create the instance repo

GitHub does not allow private forks of public repositories, so the instance is created from a
**template repository**:

1. On [this repo's GitHub page](https://github.com/industrial-curiosity/panopticon-ay-eye), click
   **Use this template → Create a new repository** and create a **private** repo in your org
   (e.g. `acme/panopticon-instance`). If the button is missing, a template-repo owner must first
   enable it at [**Settings → Template repository**](https://github.com/industrial-curiosity/panopticon-ay-eye/settings).
2. The instance repo is your org's knowledge base. It will accumulate:
   - `docs/{repo}/` — a copy of each child repo's generated documentation
   - `interfaces/{repo}.json` — one interface index shard per child repo
   - `interfaces/index.json` — the compiled org-wide index (with its `conflicts` array)
   - `panopticon.config.json` — org configuration (see step 3)
3. To pull template updates later, go to your instance repo's **Actions** tab, select
   **Sync from template**, and click **Run workflow**. If the merge produces conflicts
   (e.g. both sides modified `panopticon.config.json`), the workflow fails with
   instructions to resolve them locally. You can also enable the weekly schedule
   in the workflow file to receive updates automatically.
4. Tag the instance repo (e.g. `v1`) so child caller workflows can pin a ref (see step 3's
   `workflow_ref`).

## 2. Configure org-level secrets and variables

Go to your org's **Settings → Secrets and variables → Actions (https://github.com/organizations/YOUR-ORG/settings/secrets/actions)**
(replace `YOUR-ORG` with your GitHub org slug).

For each secret and variable below, set **Repository access → Selected repositories** and add:
- the **instance repo** (created in step 1), and
- every **child repo** Panopticon should cover.

Make sure that your token is visible to your instance repository as well as your child repositories.

The instance repo needs access because the Sync from template workflow runs there.
Child repos never configure per-repo secrets or variables — their caller workflows are
trivial references to the shared workflows.

**Secrets** (encrypted; never visible in logs):

| Secret | What it is |
| --- | --- |
| `PANOPTICON_LLM_API_KEY` | Bearer token for the LLM endpoint |
| `PANOPTICON_INSTANCE_TOKEN` | Fine-grained PAT scoped to the instance repo — [see instructions below](#creating-panopticon_instance_token) |

**Variables** (plaintext; visible in logs):

| Variable | What it is |
| --- | --- |
| `PANOPTICON_LLM_ENDPOINT` | Base URL of any litellm-compatible (OpenAI `/chat/completions`) endpoint |
| `PANOPTICON_LLM_MODEL` | Model name passed to the endpoint (defaults to `default`, which litellm proxies commonly alias) |

These are consumed only by the shared CI workflows. Local flows — initialization, doc generation,
index updates — run in each developer's own AI agent harness and need none of them.

### Creating PANOPTICON_INSTANCE_TOKEN

1. Go to [**New fine-grained personal access token**](https://github.com/settings/personal-access-tokens/new).
2. Set **Resource owner** to your org (e.g. `acme`).
3. Under **Repository access**, choose **Only select repositories** and add your **instance repo**
   — the private repo you created in step 1 (e.g. `acme/panopticon-instance`). This is not a child
   repo; it is the central knowledge-base repo that all child repos push into.
4. Under **Permissions → Repository permissions**, add:
   - **Contents** → Read and write
   - **Issues** → Read and write
   - **Workflows** → Read and write *(required to push `.github/workflows/` files during sync)*
   - *(Metadata → Read-only is added automatically by GitHub)*
5. Set an expiration, click **Generate token**, and copy it immediately.
6. Add the copied token as the `PANOPTICON_INSTANCE_TOKEN` org secret at
   **Settings → Secrets and variables → Actions (https://github.com/organizations/YOUR-ORG/settings/secrets/actions)**.

## 3. Org configuration

`panopticon.config.json` at the instance repo root:

```json
{
  "schema_version": 1,
  "gating": {
    "init": "blocking",
    "doc-drift": "blocking",
    "interface-conflict": "advisory"
  },
  "workflow_ref": "v1"
}
```

- **`gating`** — per-check outcomes. Defaults: initialization and doc-drift checks **fail** the
  workflow when they find a problem; interface-conflict checks are **advisory** (reported but
  passing) because LLM-extracted entries can false-positive. Each check type can be moved in
  either direction.
- **`workflow_ref`** — the git ref (tag or branch) at which the init tooling wires child caller
  workflows to the instance's reusable workflows. A pinned tag is the safe default; a branch
  gives you rolling updates.

## 4. Initialize a child repo

Initialization has three phases: a deterministic bootstrap, an AI agent pass, and a final validation step.

### Phase 1 — Bootstrap (from the child repo, no AI needed)

Run the bootstrap script from inside the child repo. It will prompt for your instance slug if
`PANOPTICON_INSTANCE` is not already set:

```bash
cd my-service
export PANOPTICON_INSTANCE=acme/panopticon-instance
curl -fsSL "https://raw.githubusercontent.com/${PANOPTICON_INSTANCE}/main/install.py" | python3

# or call it directly and enter it again when prompted
curl -fsSL "https://raw.githubusercontent.com/acme/panopticon-instance/main/install.py" | python3
```

The script will:
- Install the Panopticon skills into `.agents/skills/`
- Wire the three caller GitHub Actions workflows into `.github/workflows/`
- Check that org secrets and variables are configured (report-only — nothing is blocked)
- Print the exact prompts to give your AI agent in Phase 2

### Phase 2 — Agent (follow the printed prompts)

Copy the prompts the bootstrap script printed and give them to your AI agent (Claude Code, Cursor,
or any harness that loads skills from `.agents/skills/`). The agent will:
1. Generate the four-layer documentation using the `panopticon-doc-generation` skill
2. Build the local interface index (`panopticon/index.json`) using the
   `panopticon-interface-naming` and `panopticon-interface-extraction` skills

No `PANOPTICON_LLM_*` secrets or variables are needed locally — the agent uses its own harness.

### Phase 3 — Finalize

The final prompt from the bootstrap output will instruct your agent to run the finalization step,
which validates the agent-produced docs and index and writes `panopticon/config.json` — the
initialization flag — only once validation passes.

### Commit and push

```bash
git add .github/workflows/ .agents/skills/ docs/ panopticon/
git commit -m "chore: initialize Panopticon"
git push
```

## 5. What runs afterwards

- **Every PR:** initialization check, doc-drift check, index-currency check, pre-merge conflict
  simulation against the compiled index (results as a PR comment), and a push of the PR's
  docs/index state to the `{repo}/{branch}` branch of the instance repo.
- **Every merge to main:** docs copied to `docs/{repo}/`, shard replaced, compiled index rebuilt
  and pushed directly to the instance repo; conflict issues opened/updated in both repos when the
  merge produces conflicts.
- **Every PR close:** the matching `{repo}/{branch}` instance branch is deleted.
