# Org-owner setup guide

How to stand up Panopticon for an organization: create your private instance from this template,
configure org secrets, tune gating, and initialize child repos.

## 1. Create the instance repo

GitHub does not allow private forks of public repositories, so the instance is created from a
**template repository**:

1. On this repo's GitHub page, use **Use this template → Create a new repository** and create a
   **private** repo in your org (e.g. `acme/panopticon-instance`). If the button is missing, a
   template-repo owner must first enable **Settings → Template repository**.
2. The instance repo is your org's knowledge base. It will accumulate:
   - `docs/{repo}/` — a copy of each child repo's generated documentation
   - `interfaces/{repo}.json` — one interface index shard per child repo
   - `interfaces/index.json` — the compiled org-wide index (with its `conflicts` array)
   - `panopticon.config.json` — org configuration (see step 3)
3. To pull template updates later, run the **Sync from template** workflow from
   **Actions → Sync from template → Run workflow**. If the merge produces conflicts
   (e.g. both sides modified `panopticon.config.json`), the workflow fails with
   instructions to resolve them locally. You can also enable the weekly schedule
   in the workflow file to receive updates automatically.

4. Tag the instance repo (e.g. `v1`) so child caller workflows can pin a ref (see step 3's
   `workflow_ref`).

## 2. Configure org-level secrets

All three secrets are **organization-level** Actions secrets (org **Settings → Secrets and
variables → Actions**), granted to every repo Panopticon should cover. Child repos never
configure per-repo secrets — their caller workflows are trivial references to the shared
workflows.

| Secret | What it is |
| --- | --- |
| `PANOPTICON_LLM_ENDPOINT` | Base URL of any litellm-compatible (OpenAI `/chat/completions`) endpoint |
| `PANOPTICON_LLM_API_KEY` | Bearer token for that endpoint |
| `PANOPTICON_INSTANCE_TOKEN` | Fine-grained PAT scoped to the instance repo with **contents: read/write** and **issues: read/write** |

Optionally set the org-level **variable** `PANOPTICON_LLM_MODEL` if your endpoint routes models
by name (defaults to `default`, which litellm proxies commonly alias).

These secrets are consumed only by the shared CI workflows. Local flows — initialization, doc
generation, index updates — run in each developer's own AI agent harness and need none of them.

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

Initialization is a two-step dance between the developer's agent and deterministic tooling:

1. **Agent step (local, no Panopticon secrets):** in the child repo, have your AI agent follow
   the bundled skills — `panopticon-doc-generation` for the four documentation layers and
   `panopticon-interface-naming` / `panopticon-interface-extraction` for the local index
   (`panopticon/index.json`). The skills live in the instance checkout under `.agents/skills/`.
2. **Tooling step:** from the instance repo checkout, run:

   ```bash
   python3 -m panopticon.init_repo --child ../my-service --instance acme/panopticon-instance
   ```

   The tooling adopts the repo's existing documentation location (or asks, defaulting to
   `docs/`), validates the agent-produced docs and index, wires the three caller workflows, and
   writes `panopticon/config.json` — the initialization flag — only when validation passes. It
   also verifies the org secrets exist (report-only; missing secrets never block local init).
   Re-running init is idempotent.

3. Commit and push the child repo changes (workflows, docs, `panopticon/` directory).

## 5. What runs afterwards

- **Every PR:** initialization check, doc-drift check, index-currency check, pre-merge conflict
  simulation against the compiled index (results as a PR comment), and a push of the PR's
  docs/index state to the `{repo}/{branch}` branch of the instance repo.
- **Every merge to main:** docs copied to `docs/{repo}/`, shard replaced, compiled index rebuilt
  and pushed directly to the instance repo; conflict issues opened/updated in both repos when the
  merge produces conflicts.
- **Every PR close:** the matching `{repo}/{branch}` instance branch is deleted.
