## 1. Index core (interface-indexing)

- [x] 1.1 Define the JSON index schema (schema_version, keyed entries with consumer/producer repo-object
      lists, conflicts array) and write fixture files
- [x] 1.2 Implement index load/validate/save with stdlib-only Python (`panopticon/` package layout)
- [x] 1.3 Implement shard replace + deterministic compiled-index rebuild
- [x] 1.4 Implement entry matching and conflict detection (consumer match, owner match, conflict entries)
- [x] 1.5 Implement `simulate_merge` as a dry-run of the same merge code path, emitting a report structure
- [x] 1.6 Implement the parser registry (`detect`/`extract` contract) and the REST/OpenAPI starter parser
- [x] 1.7 Add the Kafka topic-config starter parser
- [x] 1.8 Implement deterministic name-normalization rules and `panopticon-` hint-comment parsing (hints
      honored first), applied at extraction and merge time so shards store canonical names and compile stays
      LLM-free
- [x] 1.9 Unit tests over fixtures: merge, compile reproducibility, conflict cases, simulation parity with merge

## 2. Agent runtime (agent-runtime)

- [x] 2.1 Implement the stdlib HTTP client (CI-only execution path) for OpenAI-compatible `/chat/completions`
      against `PANOPTICON_LLM_ENDPOINT` / `PANOPTICON_LLM_API_KEY`, with retry and timeout
- [x] 2.2 Implement skill loading (markdown instruction files → system prompt)
- [x] 2.3 Implement fail-loudly behavior when the endpoint or any other requirement is missing or unreachable
      (clear error naming what is missing and how to provide it)
- [x] 2.4 Tests with a stub HTTP server: request shape, retries, degradation paths

## 3. Extraction and doc generation (interface-indexing + doc-generation)

- [x] 3.1 Implement LLM extraction fallback: candidate-file selection, `extracted_by: llm` tagging, parser-gap
      recommendations in the workflow summary
- [x] 3.2 Write the harness-portable doc-generation skill files and templates for the four layers (architecture
      overview, per-component, interface, operational) — runnable in any agent harness and by the CI runtime
- [x] 3.3 Implement deterministic interface-doc rendering from the local index
- [x] 3.4 Implement doc regeneration in place, including removal of docs for deleted components
- [x] 3.5 Implement the LLM doc-drift check (diff + docs in, verdict + reasons out), failing loudly with
      remediation guidance when docs are stale
- [x] 3.6 Write the interface naming/matching skill (LLM judgment layered over hints and normalization rules;
      persists judgments as `panopticon-interface` hint comments; local agents judge and write hints, CI fails
      on unresolvable names with an instruction to add a hint)

## 4. Repo initialization (repo-initialization)

- [x] 4.1 Implement the init tooling: caller-workflow wiring at the org-configured ref, validation that the
      agent-produced docs and index meet requirements, `panopticon/config.json` written only after validation
      passes — no `PANOPTICON_LLM_*` needed locally
- [x] 4.2 Implement org-level secret and variable verification with actionable setup instructions (secrets
      `PANOPTICON_LLM_API_KEY`/`PANOPTICON_INSTANCE_TOKEN` and variables `PANOPTICON_LLM_ENDPOINT`/
      `PANOPTICON_LLM_MODEL` checked separately via the gh API; child repos need no per-repo configuration;
      missing items must not block local init steps)
- [x] 4.6 Add test for missing org-level variable scenario: verify that `verify_org_secrets` reports a clear
      message with setup instructions when a variable such as `PANOPTICON_LLM_ENDPOINT` is absent (mirrors
      existing `test_missing_secret_reported_with_instructions`)
- [x] 4.3 Make re-initialization idempotent (update in place, no duplicates)
- [x] 4.4 Implement documentation-location adoption: existing docs adopted and aligned; otherwise prompt with
      `docs/` default; record the location in `panopticon/config.json`
- [ ] 4.5 Test initialization end-to-end against a sandbox child repo (blocked locally: needs a sandbox GitHub
      org/repo; unit coverage in `tests/test_init_repo.py` exercises the full local flow against a temp repo)

## 5. Instance repo structure and config

- [x] 5.1 Define the instance repo layout (`docs/{repo}/`, `interfaces/`, `panopticon.config.json`); marking
      the repo as a GitHub template repository is a manual owner step documented in the setup guide
- [x] 5.2 Implement `panopticon.config.json` reading (gating modes per check type, workflow ref policy) with
      per-check defaults: init and doc-drift fail, interface-conflict advisory

## 6. PR evaluation workflows (pr-evaluation)

- [x] 6.1 Write the reusable PR workflow: initialization check with skip-and-instruct behavior
- [x] 6.2 Add the doc-drift check step with PR comment output, failing by default when docs are stale
- [x] 6.3 Add pre-merge simulation: index-currency check (CI agent evaluates the diff plus minimal context),
      fetch compiled index via `PANOPTICON_INSTANCE_TOKEN`, dry-run merge, PR comment + CI summary
- [x] 6.4 Add the `{repo}/{branch}` state push to the instance repo
- [x] 6.5 Wire gating configuration into check outcomes (per-check defaults, org overrides in both directions)
- [ ] 6.6 Test the PR workflow in a sandbox org (conflict PR, clean PR, uninitialized repo) (blocked locally:
      needs a sandbox GitHub org; the Python CLIs the workflow invokes are unit-tested)

## 7. Master sync workflows (master-sync)

- [x] 7.1 Write the reusable merge-to-main workflow: docs copy, shard replace, compiled rebuild, direct push
- [x] 7.2 Implement the fetch-rebase-retry loop for concurrent pushes
- [x] 7.3 Implement conflict-issue creation in both repos with cross-links, updating at most one open issue
      per child repo in each repository
- [x] 7.4 Write the PR-close workflow deleting the matching `{repo}/{branch}` instance branch
- [ ] 7.5 Test merge sync in the sandbox org (clean merge, conflicting merge, concurrent merges) (blocked
      locally: needs a sandbox GitHub org; merge/retry logic is unit-tested via the merge CLI)

## 8. Documentation

- [x] 8.1 Write template-repo docs: org-owner setup guide (create instance from template, secrets, variables,
      config) and parser contribution guide
- [x] 8.2 Update README.md and docs/FUSE Panopticon Strategy.md to reflect any user-facing or architectural
      changes introduced by this change
