# 2026 07 11 Establish Panopticon Core Proposal

## Why

Organizations with many repositories have no reliable, automated view of how
their services connect, so
cross-repo breaking changes are discovered at deploy time instead of review
time, and per-repo documentation
drifts from the code. Panopticon exists to solve this, but the repository is
currently an empty template —
this change establishes the core capabilities that make it usable end to end.

## What Changes

- Introduce the Python core tooling: interface index schema, per-repo shard
  merge/compile, conflict detection,
  and the deterministic parser framework (stdlib-first, checkout-and-run).
- Introduce the provider-agnostic agent runtime for CI: LLM calls via
  `PANOPTICON_LLM_API_KEY` /
  `PANOPTICON_LLM_ENDPOINT`, litellm-compatible endpoints first.
- Introduce the initialization flow: the user's agent generates the four-layer
  documentation and local
  interface index via bundled skills; deterministic tooling wires the shared
  workflows, validates the results,
  and writes the repo's `panopticon/config.json` (initialization flag plus repo
  settings) only once they meet
  requirements.
- Introduce shared PR-evaluation workflows: init check, doc-drift check,
  pre-merge index simulation with PR
  comments, and pushing PR docs/index state to a `{repo}/{branch}` branch in the
  instance repo.
- Introduce the merge-to-main sync workflow: direct push of docs and index shard
  to the instance repo, compiled
  index rebuild, and issue creation in both repos on conflict.
- Introduce org configuration in the instance fork: gating per check type (init
  and doc-drift fail by default,
  interface conflicts advisory by default; orgs can adjust) and workflow ref
  policy.

## Capabilities

### New Capabilities

- `agent-runtime`: provider-agnostic LLM invocation from CI workflows —
  endpoint/key configuration,
  litellm-compatible request shape, prompt/skill loading, and failure behavior
  when the LLM is unavailable.
  Local flows (initialization, doc updating) run the same skills in the user's
  preferred agent harness and
  need no Panopticon LLM configuration.
- `interface-indexing`: the interface index schema and semantics — entry
  structure, code-state-not-deployment
  semantics (branches first-class, environments excluded), name normalization
  and LLM-assisted matching,
  deterministic parser framework, LLM extraction fallback with parser-gap
  recommendations, shard merge/compile,
  and conflict-entry detection.
- `repo-initialization`: the init script run from an instance fork against a
  child repo — workflow wiring,
  secret requirements, initial doc and index generation, and the
  `panopticon/config.json` initialization/config
  file.
- `doc-generation`: the four documentation layers (architecture overview,
  per-component, interface,
  operational), their structure and regeneration rules, and doc-vs-code drift
  detection.
- `pr-evaluation`: the shared PR workflows — initialization check, doc-drift
  check, pre-merge index simulation
  against the instance repo's compiled index, PR comment reporting,
  `{repo}/{branch}` state push, and
  org-configurable gating.
- `master-sync`: the merge-to-main workflow — docs copy to `docs/{repo}/`,
  whole-shard index replace, compiled
  index rebuild, conflict issue creation in both repos, and `{repo}/{branch}`
  branch lifecycle.

### Modified Capabilities

None — this is the first change; no specs exist yet.

## Impact

- New Python package/scripts in this template repo (index tooling, parsers, init
  script).
- New reusable GitHub Actions workflows under `.github/workflows/`.
- New agent skills for doc generation and extraction alongside the existing
  ground-rule skills in
  `.agents/skills/`.
- New org-level secrets, consumed only by the shared CI workflows (not by local
  tooling, and never configured
  per child repo): `PANOPTICON_LLM_API_KEY`, `PANOPTICON_LLM_ENDPOINT`,
  `PANOPTICON_INSTANCE_TOKEN`.
- Instance forks gain `docs/{repo}/`, `interfaces/` (shards + compiled index),
  and an org config file.
- No existing systems are affected; the repo currently contains only
  documentation and OpenSpec scaffolding.
