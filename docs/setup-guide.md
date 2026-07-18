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
   in the workflow file to receive updates automatically. Any path listed in your org config's
   `protected_paths` (step 3 below) always survives this sync unchanged — see that section for
   how to declare instance-level customizations.
4. No tagging is required to get started — child caller workflows default to the instance repo's
   default branch until you opt into pinning a ref (see step 3's `workflow_ref`).

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
    "interface-conflict": "advisory",
    "diagram-missing": "advisory"
  },
  "protected_paths": [".agents/skills/panopticon-doc-generation/references/custom.md"],
  "internal_registries": ["packages.example.com"]
}
```

- **`gating`** — per-check outcomes. Defaults: initialization and doc-drift checks **fail** the
  workflow when they find a problem; interface-conflict checks are **advisory** (reported but
  passing) because LLM-extracted entries can false-positive; diagram-missing checks are
  **advisory** at first so already-initialized repos aren't immediately blocked before they've
  regenerated docs to pick up the new `## Architecture diagram` section — flip it to `blocking`
  once your repos have backfilled. Each check type can be moved in either direction.
- **`workflow_ref`** *(optional)* — the git ref (tag or branch) at which the init tooling wires child
  caller workflows to the instance's reusable workflows. Omit it and the instance repo's default branch
  is used — no tagging required to get started. Set it once you want to pin caller workflows to a
  specific tag or branch instead.
- **`protected_paths`** *(optional, default `[]`)* — literal paths (skills, vendored tooling modules,
  or other instance-repo content) your org has customized at the instance level, which
  `sync-from-template` must never overwrite. Unlike `panopticon.diagram.config.json`'s protection
  (a template-declared, fixed registry), these are org-declared and open-ended — list any exact file
  path you've customized. Protection is applied via `.git/info/attributes` on every sync run (never
  a commit, never the tracked `.gitattributes`), so it's invisible in the tracked tree; each sync run's
  GitHub Actions step summary lists which paths were protected that run as the audit trail. Entries
  are exact file paths, not directory globs — list each customized file individually.
- **`internal_registries`** *(optional, default `[]`)* — host or URL substrings identifying your org's
  own private package registry/registries (e.g. an Artifactory or Nexus host). Dependency-indexing uses
  this to recognize that a repo's dependency resolves from your org's own infrastructure rather than a
  third-party one — the same field covers both a consumer repo installing an internal package and a
  producer repo publishing one, so you configure your registry identity once, not per ecosystem.
  Ecosystems whose dependency declarations already embed your org's identity (e.g. Go module paths
  under your org's GitHub organization) need no entry here at all. When a dependency or interface
  can't be resolved automatically, developers pin it with a hint comment — see
  `docs/hint-reference.md` for every hint form and exactly how each one behaves.

## 4. Initialize a child repo

Initialization has three phases: a deterministic bootstrap, an AI agent pass, and a final validation step.

### Phase 1 — Bootstrap (from the child repo, no AI needed)

Run the public template launcher from inside the child repo. The same command supports public and private
instance repositories:

```bash
cd my-service
curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | python3
```

The launcher asks for any missing interactive inputs, authenticates when the selected instance is private,
and then runs that instance repository's own installer. Set stable inputs before repeat or non-interactive
runs:

```bash
export PANOPTICON_INSTANCE=YOUR-ORG/YOUR-INSTANCE-REPO
export PANOPTICON_SKILLS_LOCATION=.agents/skills
# Optional: select a branch, tag, or commit instead of the instance's default branch.
export PANOPTICON_INSTANCE_REF=YOUR-INSTANCE-REF
```

For example, use `PANOPTICON_INSTANCE=acme/panopticon-instance` and
`PANOPTICON_INSTANCE_REF=release-2026-07`. Private instances use `GH_TOKEN`, `GITHUB_TOKEN`, or an existing
`gh auth` session. Supply tokens through your shell or CI secret environment; never place one directly in
the command. The instance installer chooses where skills live (template default `.agents/skills/`; see
[`docs/agentskills-support.md`](agentskills-support.md)). Set `PANOPTICON_SKILLS_LOCATION` to skip that
prompt for non-interactive or CI runs.

Once a location is chosen, the script will:

- Install the Panopticon skills there
- Vendor the local-tooling subset of the `panopticon` Python package into `panopticon/`, so the
  `python3 -m panopticon...` commands the skills use in Phase 2 work immediately — no need to clone the
  instance repo or set up a Python environment yourself
- Download `PANOPTICON.md` to the repo root — a concise getting-started guide (how the system works,
  where architecture diagrams live, and how to keep this repo's skills/tooling current)
- Wire the three caller GitHub Actions workflows into `.github/workflows/`
- Check that org secrets and variables are configured (report-only — nothing is blocked)
- Print a reminder of `PANOPTICON.md` and the `python3 -m panopticon.sync` command (every run, not
  just the first), then the one prompt to give your AI agent in Phase 2

### Phase 2 — Agent (follow the printed prompt)

Give your AI agent (Claude Code, Cursor, or whichever tool you configured) the printed prompt — a single
skill that sequences interface indexing, dependency indexing, documentation generation, and finalization
on its own, with a resumable checkpoint if your agent session gets interrupted partway through. Each of
the underlying skills also works standalone if you'd rather run a step by itself.

No `PANOPTICON_LLM_*` secrets or variables are needed locally — the agent uses its own harness.

### Phase 3 — Finalize

The final prompt from the bootstrap output will instruct your agent to run the finalization step,
which validates the agent-produced docs and index and writes `panopticon/config.json` — the
initialization flag — only once validation passes.

### Commit and push

Commit and push everything the process created — the bootstrap script's own final prompt gives the exact
command, since which paths that covers depends on the skills location you chose.

If initialization found and fixed documentation that contradicted the current code, it records what it
changed and why in `panopticon-changelog.md` in your docs location, instead of annotating the fix inline in
the docs themselves. Panopticon never stages or commits this file automatically — review it and decide
whether to keep, edit, or discard it before you commit.

## 5. What runs afterwards

- **Every PR:** initialization check, doc-drift check (now also judging the `## Architecture
  diagram` section's staleness alongside prose), index-currency check, a deterministic
  diagram-existence check (the section exists and parses — no LLM call, independent of doc-drift's
  accuracy judgment), pre-merge conflict simulation against the compiled index (results as a PR
  comment), a push of the PR's docs/index state to the `{repo}/{branch}` branch of the
  instance repo, and a **tooling-currency check** (see below) — always advisory, never affects the
  workflow's pass/fail outcome.
- **Every merge to main:** docs copied to `docs/{repo}/`, shard replaced, compiled index rebuilt,
  and the org-wide architecture diagram (`docs/architecture.md` in the instance repo — one section
  per repo with cross-repo interfaces, a relationship diagram, and a table) rebuilt from the fresh
  compiled index, all pushed directly to the instance repo in the same commit; conflict issues
  opened/updated in both repos when the merge produces conflicts.
- **Every PR close:** the matching `{repo}/{branch}` instance branch is deleted.

Diagram rendering format defaults to Mermaid and is configurable per instance via
`panopticon.diagram.config.json` at the instance repo root — this file is protected from
`sync-from-template`'s merge (your customization always wins), and syncing warns (non-blocking) if
the template adds or removes a config field you haven't picked up.

## 6. Keeping a child repo's skills and tooling current

Every child repo gets a `PANOPTICON.md` at its root from the bootstrap script (Phase 1) — a concise
version of this section, so a maintainer working in that repo doesn't need this setup guide open to
remember how to stay current. The bootstrap script also reprints the sync command below on every
run, first bootstrap and re-run alike.

A child repo's downloaded skills, vendored `panopticon/` tooling, and wired workflow ref are all
snapshots taken at bootstrap time. Nothing forces them to stay current — the **tooling-currency
check** (every PR, see above) warns, non-blocking, when any of the three has drifted from the
instance repo's current default branch: the wired ref no longer resolves to the instance's tip
commit, or a skill/tooling file's content differs, is missing, or is extra. It's always advisory
and never gated — acting on it is entirely at your discretion.

To pull the instance's current skills and tooling into an already-bootstrapped child repo:

```bash
python3 -m panopticon.sync
```

This overwrites the repo's skills and vendored `panopticon/` tooling unconditionally — there is no
per-file protection at the child layer. Review `git diff`/`git status` before committing; anything
you disagree with, don't commit or hand-edit back. To see what would change without writing
anything:

```bash
python3 -m panopticon.sync --check-updates
```

If you've customized a skill or tooling module at the **instance** level and want that
customization to survive both this script's overwrite and `sync-from-template`'s pulls from the
upstream template, declare it in the instance's `panopticon.config.json` under `protected_paths`
(step 3) — `sync.py` does not consult `protected_paths` itself (it always overwrites the child
unconditionally by design); `protected_paths` only protects the *instance* repo's own copy from the
*template*.

## 7. Finding the org-wide architecture diagram from a child repo

A child repo's `README.md` already links to both diagrams at the top — its own (relative, resolves once
merged into the instance) and the org diagram (a fully-qualified GitHub URL, clickable immediately). The
`## Architecture diagram` section's own back-link is relative too, and only resolves once this repo's docs
have been merged into the instance repo (see the architecture-diagrams capability) — it won't work if you
click it before then. To regenerate the immediately-clickable org link yourself, from your own checkout,
before any merge:

```bash
python3 -m panopticon.org_diagram_link
```

This prints a single resolvable URL, e.g. `https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a`.
It reads `panopticon/config.json`'s `instance_default_branch` field first — no network call in that
case — resolved automatically during Phase 3 finalization and refreshed on every bootstrap rerun
(`GH_TOKEN`/`GITHUB_TOKEN`, or a token extracted via `gh auth token`; never requires `gh auth login`
specifically). If that field is genuinely missing, the script attempts a live lookup itself before
giving up, using the same token resolution — no separate command needed.
