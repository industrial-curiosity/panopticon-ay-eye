## Context

Panopticon is currently an empty template: strategy docs, ground-rule skills, and OpenSpec scaffolding, but no
tooling or workflows. This design covers the first implementable slice of all six core capabilities. The
architecture decisions recorded in `.agents/skills/panopticon-architecture` (hybrid execution, push-based sync,
shard + compiled index, advisory-default gating, provider-agnostic agents) are settled inputs to this design,
not open questions.

## Goals / Non-Goals

**Goals:**

- A child repo can be initialized from an instance fork and end up with docs, a local index, wired workflows,
  and a `panopticon/config.json` (initialization flag plus repo settings).
- PRs in an initialized repo get doc-drift and interface-conflict feedback as comments, and their state is
  mirrored to `{repo}/{branch}` in the instance repo.
- Merges to main update the instance repo (docs, shard, compiled index) and open issues on conflict.
- All of the above works with any litellm-compatible LLM endpoint and minimal Python requirements.

**Non-Goals:**

- Parser coverage breadth — ship the framework plus a small starter set (REST/OpenAPI, Kafka topic config);
  growth happens via the upstream-contribution loop.
- Instance-to-template upstream sync automation (orgs pull template updates manually for now).
- Non-GitHub hosting (GitLab etc.).
- Deployment/environment awareness — the index describes code state only.
- Pruning of orphaned `{repo}/{branch}` instance branches beyond PR-close deletion — deferred until explicitly
  required.
- Visualizations over the central docs highlighting conflicts and misalignments — future work.

## Decisions

### D1: Instance repos are created from a GitHub template, not a git fork

GitHub does not allow private forks of public repositories. The template repo is marked as a **template
repository**, and org owners create their private instance via "Use this template". Template updates are pulled
by adding the template as a git remote; the template repo ships `sync-from-template.yml` so instance owners
do not have to set this up manually.

"Use this template" creates a repo with no shared git history, so the first sync has no common ancestor.
`sync-from-template.yml` detects this and resolves add/add conflicts with `-X theirs` automatically — safe
because the instance at that point contains only files that came from the template. Subsequent syncs use the
normal merge strategy. The strategy doc's word "fork" is interpreted as "private copy".

### D2: Index files are JSON with an explicit schema version

- Child repo local index: `panopticon/index.json`; child repo config: `panopticon/config.json`, doubling as
  the initialization flag and recording repo-level settings (documentation location).
- Instance repo shards: `interfaces/{repo}.json` (whole-file replaced on merge).
- Instance repo compiled index: `interfaces/index.json`, rebuilt deterministically from shards; never edited by
  tooling in place.
- Every file carries `schema_version` so template upgrades can migrate.

JSON over YAML because the stdlib parses JSON natively (see `panopticon-python-tooling`); this also applies to
the org config file (`panopticon.config.json` in the instance repo, holding gating mode and workflow ref
policy). Conflict entries exist only in the instance repo: the compiled index carries a dedicated `conflicts`
array, recomputed deterministically on every rebuild, so a shard replace naturally clears a repo's stale
conflicts. Local repo indexes never contain conflicts — a repo only knows what it knows.

### D3: Branch state maps to instance-repo branches verbatim

The instance branch name is `{repo}/{branch}` with no escaping: repository names cannot contain `/`, so the
first path segment is always unambiguous, and git branch names support nested slashes. The instance repo's
default branch holds merged state only. PR-close (merged or abandoned) deletes the matching instance branch via
a workflow triggered on `pull_request: closed`.

### D4: Pre-merge simulation is a pure function over two JSON documents

`simulate_merge(local_index, compiled_index) -> report`. The PR workflow fetches `interfaces/index.json` from
the instance repo's default branch (read via `PANOPTICON_INSTANCE_TOKEN`), runs the same merge code used at
merge time in dry-run mode, and posts the report as a PR comment. One code path for simulation and real merge
prevents drift between what PRs predict and what merges do.

### D5: LLM access is a thin stdlib HTTP client

A single Python module speaks the OpenAI-compatible `/chat/completions` shape over `urllib` against
`PANOPTICON_LLM_ENDPOINT` with `PANOPTICON_LLM_API_KEY`. No provider SDKs, no agent frameworks. Skills
(markdown instruction files) are loaded as system-prompt content by this client. If the endpoint is
unreachable or unconfigured, LLM-dependent checks emit a clear "skipped" status in the CI summary rather than
failing structurally deterministic checks.

The client is the CI execution path only. Local flows — child-repo initialization, doc updating, and interface
indexing — execute the same skill files in the user's preferred AI agent harness, so developer machines need no
`PANOPTICON_LLM_*` configuration. The skill files are the shared contract between the two execution paths.
When a CI requirement (endpoint, key, token) is missing or unreachable, the workflow fails loudly, naming
exactly what is missing — a silent skip would falsely imply the checks passed.

### D6: Workflows are reusable workflows referenced from the instance repo

Child repos get thin caller workflows (`uses: <org>/<instance>/.github/workflows/panopticon-pr.yml@<ref>`)
written by the bootstrap installer script. The ref is org-configurable via `workflow_ref` in the instance's
`panopticon.config.json`; the template default (when unset) is the instance repo's default branch, so a
fresh instance needs no manual tagging step before child repos can initialize. Org owners can still opt
into pinning a tag or branch. Automated tag-based release versioning of the instance repo is deferred to a
future change. The bootstrap script fetches skills and workflows from the instance repo via the GitHub API
— no local clone of the instance repo is required. CI steps run by checking out the instance repo and
invoking scripts directly — no pip package, no build step.

### D7: Cross-repo auth is a fine-grained PAT (GitHub App later)

`PANOPTICON_INSTANCE_TOKEN` is a fine-grained PAT scoped to the instance repo with `contents: read/write` and
`issues: write`, configured as an org-level secret so all child repos inherit it. Panopticon's CI configuration
is split by sensitivity: **secrets** (`PANOPTICON_LLM_API_KEY`, `PANOPTICON_INSTANCE_TOKEN`) for credentials,
and **variables** (`PANOPTICON_LLM_ENDPOINT`, `PANOPTICON_LLM_MODEL`) for non-sensitive configuration. All are
org-level: child repos never configure per-repo secrets or variables — their caller workflows are trivial
references to the shared workflows. A GitHub App is the cleaner long-term answer but adds setup burden; the
token interface is a single env var either way, so swapping later is non-breaking.

### D8: Parser framework is a registry of self-contained modules

Each parser is one Python module exposing `detect(repo_root) -> bool` and `extract(repo_root) -> entries`,
registered by interface type. Extraction runs all detecting parsers, then hands remaining candidate files to
the LLM extractor; LLM-extracted entries are tagged `"extracted_by": "llm"` and generate the parser-gap
recommendation in the workflow summary.

### D9: Canonical names are fixed at merge time, not compile time

Interface naming and matching combine deterministic normalization rules with LLM judgment (via the bundled
skills), applied whenever entries are produced or merged — extraction, PR simulation, shard merge. Judgments
are persisted as `panopticon-`-prefixed hint comments in the code or configuration files referencing the
interface (e.g. `# panopticon-interface <name>`), which extraction honors before rules or LLM judgment — so
repeated runs are deterministic and simulate/merge parity holds. LLM naming judgment happens only locally: in
CI, a name that cannot be resolved from hints and rules fails the check with an instruction to add a hint.
Shards therefore always store canonical names, and the
compiled-index rebuild stays a deterministic, LLM-free union of shards, preserving byte-identical
reproducibility.

### D10: Combined report is assembled once, at the end, not appended progressively

The doc-drift, index-currency, and pre-merge-simulation checks each still run as independent workflow steps
(so each is individually gated), but none of them write directly to `$GITHUB_STEP_SUMMARY` anymore. Each
writes its findings to its own report file only; a final step reads all three files after every check has
run and assembles the single combined report — TL;DR, then per-check detail, then the same TL;DR repeated —
writing it once to both `$GITHUB_STEP_SUMMARY` and the PR comment. This is required because a true
lead-with-TL;DR structure needs to know every check's findings before writing the first line, which is
incompatible with each step progressively appending its own section as it completes.

## Risks / Trade-offs

- [LLM extraction produces false interface entries] → Advisory-default gating; conflict entries instead of
  hard failures; `extracted_by` tag makes provenance visible; deterministic parsers replace LLM extraction
  over time.
- [Concurrent merges race the compiled-index rebuild in the instance repo] → Push with fetch-rebase-retry
  loop; shards are per-repo files so the only contention is the compiled index, which is deterministically
  rebuildable from shards.
- [`{repo}/{branch}` branches accumulate if the close-trigger workflow is missed] → Accepted for v1; a pruning
  strategy is deliberately deferred until explicitly required.
- [Org-level PAT grants every child repo write access to the instance repo] → Acceptable for v1 (instance repo
  is documentation/index only, fully regenerable from child repos); GitHub App tightens this later.
- [Doc-drift judgment is subjective] → Drift check reports concrete reasons and remediation in the PR comment;
  it fails by default so developers know docs must be updated, and orgs can downgrade it to advisory while
  calibrating.

## Migration Plan

Greenfield — no existing deployments. Implementation order follows capability dependencies: interface-indexing
core (schema + merge/simulate) → agent-runtime → doc-generation → repo-initialization → pr-evaluation →
master-sync. Each stage is testable without the later ones (index tooling via fixtures, workflows via a
sandbox org).

## Open Questions

- Branch-dimension consumption: does the pre-merge simulation ever need to consider *other* repos' in-flight
  `{repo}/{branch}` state, or only the compiled main index? (v1: main index only.)
- Parser contribution process: PR template and acceptance criteria for upstreaming org-grown parsers.
- Schema migration tooling: needed before the first `schema_version` bump; out of scope for v1.
