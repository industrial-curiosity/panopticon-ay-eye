# Production rollout hardening action plan

This plan converts the lessons in
[`combined learnings.md`](../combined%20learnings.md) into ordered changes to
Panopticon's code, specifications, tests, process documentation, and reusable
organization setup assets. It is an implementation handoff, not a record that
the listed work has already been completed.

## How to use this plan

Work in numbered order and do not skip a pass gate. A later item may be hidden
by an earlier failure, especially on the Bedrock path.

For each numbered step:

- **Do** defines the deliverable.
- **Where** names the primary files or artifact families.
- **Pass** is the evidence required before proceeding.
- **Fail** names the recovery action when the gate does not pass.

Use one OpenSpec change per numbered implementation step unless two adjacent
steps are explicitly grouped below. Do not add this work to
`surface-org-interface-conflicts`: every task in that change is already checked
off, and its scope is organization-diagram conflict visibility rather than
rollout hardening.

## Execution status

Status values are deliberately distinct: `unstarted`, `implemented`, `locally
verified`, and `operationally proven`. Update the affected row when a rollout
change is implemented or validated.

| Step | Status | Evidence |
| --- | --- | --- |
| 0. Baseline and existing work | implemented | `surface-org-interface-conflicts` archived; the missing pre-change baseline is recorded below. |
| 1. Workflow contract validation | locally verified | [harden-bedrock-workflow-contract](../openspec/changes/archive/2026-08-01-harden-bedrock-workflow-contract/) and [template CI hardening](../openspec/changes/harden-bootstrap-manifest-and-workflow-ci/): 640 tests, strict OpenSpec validation, and reusable-workflow discovery passed on 2026-08-03. |
| 2. Bedrock request shape | locally verified | [fix-bedrock-converse-request-shape](../openspec/changes/archive/2026-08-01-fix-bedrock-converse-request-shape/) |
| 3. Local-tooling manifest | locally verified | [restrict-child-sync-tooling-manifest](../openspec/changes/archive/2026-08-02-restrict-child-sync-tooling-manifest/), [legacy-tooling guidance](../openspec/changes/archive/2026-08-02-complete-rollout-status-and-legacy-tooling-guidance/), and [JSON-manifest hardening](../openspec/changes/harden-bootstrap-manifest-and-workflow-ci/): 640 tests and strict OpenSpec validation passed on 2026-08-03. |
| 4. Effective provider requirements | locally verified | [model-effective-provider-requirements](../openspec/changes/archive/2026-08-02-model-effective-provider-requirements/) — focused provider coverage: 218 tests; full suite: 632 tests; strict OpenSpec and reusable-workflow contract validation passed on 2026-08-02. |
| 5. Negative scope and `panopticon-ignore` | unstarted | No assigned OpenSpec change. |
| 6. Organization-scale interface names | unstarted | No assigned OpenSpec change. |
| 7. Supported four-gate operating process | unstarted | No assigned OpenSpec change. |
| 8. Complex-organization instance template | unstarted | No assigned OpenSpec change. |
| 9. Sandbox rollout | unstarted | No recorded sandbox run. |

### Baseline record

The pre-change baseline required by step 0 was not captured and cannot be
reconstructed truthfully. Record the current verification result below after
each rollout-hardening change; it is not pre-change evidence.

Current baseline: on 2026-08-02, `python3 -m unittest discover -t . -s tests`
passed all 632 tests after Step 4. This confirms the current working tree only;
it is not evidence of the state before rollout hardening began.

## Outcome and success criteria

The work is complete only when all of the following are true:

- Every reusable workflow references only declared inputs and secrets.
- A Bedrock request accepted by the supported models contains no unused
  inference controls.
- Child sync installs only the instance-published local-tooling set and never
  copies CI-only modules.
- Provider validation distinguishes values that are required from values
  supplied by workflow or instance defaults.
- Illustrative material can be excluded both by conservative defaults and by a
  deterministic author hint across all relevant Panopticon checks.
- Interface naming guidance and specifications produce names that remain
  meaningful after organization-wide shard merge.
- Setup and failure guidance identify the failed integration gate and give the
  exact recovery path at a location that survives zero-job failures, step
  failures, and timeouts.
- A generic complex-organization template can configure an instance-managed
  provider, organization-specific credential wrapper, defaults, protected
  paths, and per-child onboarding without containing Yotpo identifiers or
  credential values.
- A real sandbox child run clears workflow access, effective configuration,
  caller identity, provider credentials, provider preflight, and one real
  inference.

## Glossary

- **Template repository** — this public repository, which owns shared tooling,
  workflows, skills, specifications, and reusable setup assets.
- **Instance repository** — a private organization-specific repository created
  from the template. It owns organization configuration and permitted
  customizations.
- **Child repository** — an organization repository initialized by Panopticon.
  It owns its local documentation and index shards.
- **Zero-job failure** — GitHub rejects a reusable-workflow reference or
  expression before it creates a job. There is no step log or job summary.
- **Provider contract** — the trusted registry entry and instance-selected
  names used to generate a child caller and validate the reusable workflow.
- **Effective requirement** — a value that remains required after workflow and
  instance defaults have been applied.
- **Local-tooling manifest** — the instance-published list of `panopticon/`
  modules that may be installed in a child repository.
- **Complex-organization template** — a reviewable, generated instance overlay
  for organizations with centralized credentials, custom Actions names,
  instance-supplied defaults, and per-repository identity provisioning.

## Work tracks

| Track | Purpose | May start | Complete when |
| --- | --- | --- | --- |
| A — Runtime blockers | Repair workflow compilation and Bedrock requests | Immediately | Steps 1–2 pass |
| B — Distribution boundary | Repair child tooling sync ownership | After Step 1 is isolated in its own change | Step 3 passes |
| C — Configuration semantics | Model effective required and optional values | After Step 1 | Step 4 passes |
| D — Index quality | Add negative scope, overrides, and global naming | After Step 3 defines the shared child tooling boundary | Steps 5–6 pass |
| E — Operations and reusable setup | Improve gate diagnostics and generate the complex-organization template | Draft in parallel; validate after Steps 1–6 | Steps 7–8 pass |
| F — Rollout | Exercise the complete boundary in a sandbox instance and child | After all prior steps | Step 9 passes |

Tracks B, C, and the drafting portion of E may proceed in parallel after the
first runtime blocker is isolated. Merge and rollout still follow the numbered
order because each gate can hide the next.

## Ordered implementation steps

### 0. Record the baseline and separate existing work

#### Step 0 — Do

1. Confirm the active `surface-org-interface-conflicts` change still has every
   task complete and archive it through the normal OpenSpec archive workflow
   before starting a new change.
2. Record a baseline test result and static-workflow result before modifying
   behavior.
3. Preserve already-landed protections with regression coverage rather than
   reimplementing them:
   - provider adapters behind `LLMClient`;
   - caller-generated `id-token: write` for Bedrock;
   - isolated Python setup and pinned Bedrock dependency;
   - provider capability preflight;
   - dependency naming and extraction in `panopticon-init`;
   - empty secret/variable collection handling.
4. Create one issue-to-change map using the reference table at the end of this
   document. Record each item as `unstarted`, `implemented`, `locally verified`,
   or `operationally proven`; never collapse those states.

#### Step 0 — Where

- `openspec/changes/surface-org-interface-conflicts/`
- `openspec/specs/`
- `tests/`
- `.github/workflows/`
- `docs/testing.md`

#### Step 0 — Pass

- The completed active change is no longer available as an accidental target
  for unrelated edits.
- Baseline results and any pre-existing failures are recorded.
- Each remaining lesson has one intended OpenSpec change and no duplicate
  implementation owner.

#### Step 0 — Fail

- If the active change contains incomplete work, finish or explicitly rescope
  it before archiving.
- If the baseline is red, classify each failure as pre-existing or caused by
  the rollout-hardening branch before proceeding.

### 1. Fix reusable-workflow compilation and add contract validation

This is the most critical fix. The current Bedrock workflow references
`secrets.api_key` and `inputs.endpoint` in its doc-drift and index-currency
steps even though neither name exists in its `workflow_call` contract. GitHub
can reject the workflow before creating a job.

#### Step 1 — Do

1. Remove the LiteLLM-only API-key and endpoint mappings from both Bedrock
   check steps.
2. Add a deterministic workflow-contract validator that compares every
   `inputs.<name>` and `secrets.<name>` expression in each reusable workflow
   with its declared `workflow_call` interface.
3. Run that validator over every reusable workflow, not only the Bedrock file,
   so copy/paste regressions fail locally and in CI.
4. Add focused regression tests proving:
   - the invalid current Bedrock shape fails the validator;
   - all checked-in provider workflows pass;
   - provider-specific workflows contain no references to another provider's
     contract.
5. Update the PR-evaluation and provider-configuration specifications to make
   static interface validation normative.
6. Document the zero-job diagnostic path: read the run-page banner first,
   distinguish access denial from workflow compilation, and inspect the called
   workflow rather than only the thin child caller.

#### Step 1 — Where

- `.github/workflows/panopticon-pr-bedrock.yml`
- `.github/workflows/panopticon-pr-litellm.yml`
- `.github/workflows/panopticon-pr-openai.yml`
- `panopticon/` deterministic workflow-validation module
- `tests/test_provider_workflows.py`
- `openspec/specs/pr-evaluation/spec.md`
- `openspec/specs/llm-provider-configuration/spec.md`
- `docs/setup-guide.md`
- `docs/testing.md`

#### Step 1 — Pass

- Static validation reports no undeclared `inputs.*` or `secrets.*`
  expressions in any reusable workflow.
- Provider-workflow tests prove the Bedrock file has no `inputs.endpoint`,
  `secrets.api_key`, `PANOPTICON_LLM_ENDPOINT`, or
  `PANOPTICON_LLM_API_KEY`.
- A sandbox child can load the Bedrock reusable workflow and create a job.

#### Step 1 — Fail

- A zero-job failure is not a reason to change IAM or provider code. Read the
  run-page banner, check instance workflow access, then rerun the static
  contract validator against the exact workflow ref used by the child.

### 2. Minimize and verify the Bedrock request

The current adapter always sends `inferenceConfig.temperature`, while the
rollout evidence shows supported Claude models rejecting that field. Every
current Panopticon check uses the default temperature and does not need the
control.

#### Step 2 — Do

1. Omit `inferenceConfig` from Bedrock Converse requests until a
   provider-supported control is explicitly designed and covered.
2. Keep the shared client surface stable. The Bedrock adapter accepts but does
   not forward the shared temperature argument.
3. Add request-shape tests that compare the full Converse payload and prove no
   unused optional parameter is emitted.
4. Preserve response mapping, retry classification, structured JSON correction,
   timeout configuration, and capability preflight tests.
5. Update the agent-runtime specification to require minimal provider requests
   and omission of unsupported optional behavior.
6. Add a provider-compatibility test case or recorded sandbox check that uses
   the same model class configured for rollout, because credentials-only
   preflight does not validate the real request shape.

#### Step 2 — Where

- `panopticon/llm.py`
- `tests/test_llm.py`
- `openspec/specs/agent-runtime/spec.md`
- `docs/testing.md`

#### Step 2 — Pass

- Unit tests show a default Bedrock request contains only `modelId`, `messages`,
  and `system` when present.
- A shared Bedrock temperature argument is not forwarded to the runtime client.
- A sandbox child completes one real structured inference with the configured
  model.

#### Step 2 — Fail

- If the provider rejects another optional field, remove it unless a current
  product requirement proves it is needed. Do not expand the provider request
  merely to preserve parity with the HTTP adapter.

### 3. Publish and consume an authoritative local-tooling manifest

The current sync code manages the complete `panopticon/` directory and its tests
explicitly accept `llm.py`. That contradicts the repository-initialization
specification, which excludes CI-only modules from children.

#### Step 3 — Do

1. First reverse the contradictory tests so the suite demonstrates the defect:
   syncing `llm.py`, `drift.py`, `currency.py`, `merge.py`, `extraction.py`,
   `bootstrap.py`, or `parsers/` must fail.
2. Add a template-owned local-tooling manifest containing the exact child-safe
   module paths.
3. Make bootstrap and sync fetch the manifest from the instance's current
   authoritative source. Do not retain an independently hardcoded child
   allowlist.
4. Stage the manifest and every listed module before writing any file, so a
   refreshed sync entrypoint and its new dependency arrive atomically.
5. Keep sync additive/overwrite-only. Report unknown extra child files as
   possible legacy or child-owned files; do not delete them automatically.
6. Update tooling-currency checks to compare only manifest-owned paths and to
   report CI-only or unknown extras separately.
7. Reconcile the conflicting repository-initialization and tooling-currency
   specifications around the manifest-owned boundary.
8. Add a migration procedure for children already contaminated by CI-only
   modules. It must list candidates and require an explicit reviewed removal
   rather than deleting them during sync.

#### Step 3 — Where

- New local-tooling manifest at a template-owned path
- `panopticon/bootstrap.py`
- `panopticon/sync.py`
- `panopticon/tooling_currency.py`
- `tests/test_install.py`
- `tests/test_sync.py`
- `tests/test_tooling_currency.py`
- `openspec/specs/repo-initialization/spec.md`
- `openspec/specs/tooling-currency/spec.md`
- `docs/setup-guide.md`
- `PANOPTICON.md`

#### Step 3 — Pass

- Bootstrap and sync resolve the same manifest from the instance.
- Tests prove all required local commands import successfully from only the
  manifest-listed files.
- Tests prove CI-only modules are neither downloaded nor treated as required.
- A child with an unknown extra file receives a warning and no deletion.
- A child missing a newly added local dependency receives the manifest and full
  staged resource set in one run.

#### Step 3 — Fail

- If the refreshed sync entrypoint cannot run from an older child, verify that
  manifest retrieval and staging happen before importing newly required local
  modules. Do not fall back to copying the entire package.

### 4. Model effective provider requirements

The provider registry currently carries configured names but no
required/optional semantics. Bootstrap and finalization therefore report
workflow-defaulted or instance-supplied variables as missing.

#### Step 4 — Do

1. Extend the trusted provider contract with validated logical optionality.
   Optional entries must be a subset of the provider's registered logical
   names; arbitrary names remain invalid.
2. Include required/optional semantics in the deterministic contract revision
   and generated child caller contract.
3. Exclude optional names from bootstrap and finalization prerequisite warnings.
   Keep them visible as optional configuration in reports.
4. Resolve workflow and instance defaults before the provider's runtime
   validation step. A value marked optional without an effective default must
   still fail loudly before LLM work.
5. Keep the instance token required whenever the child must access the private
   instance. Do not let optionality weaken repository access or authentication
   requirements.
6. Handle empty secret or variable collections without printing empty,
   misleading checks or querying irrelevant APIs.
7. Add cases for:
   - stock required model value;
   - instance-supplied model default;
   - request-budget workflow defaults;
   - Bedrock `instance-managed` mode with no AWS region or role variable;
   - an invalid optional logical name;
   - an optional marker whose promised default is absent.
8. Update configuration, initialization, and setup documentation with required,
   optional, and default-source columns.

#### Step 4 — Where

- `panopticon/providers.py`
- `panopticon/config.py`
- `panopticon/configure_instance.py`
- `panopticon/callers.py`
- `panopticon/bootstrap.py`
- `panopticon/init_repo.py`
- provider workflows and recovery summaries
- provider, initialization, and PR-evaluation specifications
- `docs/setup-guide.md`
- `docs/testing.md`

#### Step 4 — Pass

- Finalization does not report a value missing when the selected trusted
  workflow or instance supplies it.
- The same configuration fails before LLM work when the declared default is
  absent.
- Changing optionality changes the provider contract revision and produces an
  exact child-bootstrap recovery command for stale callers.

#### Step 4 — Fail

- If an optional value reaches provider preflight empty, treat the default
  declaration as false configuration, correct the contract or default source,
  and rerun child bootstrap. Do not make preflight silently skip.

### 5. Add deterministic negative scope and `panopticon-ignore`

Current shared file iteration excludes generated and dependency directories but
does not exclude common example, sample, fixture, testdata, demo, or scaffold
locations. No author-controlled ignore hint exists.

#### Step 5 — Do

1. Add one deterministic scope policy shared by interface parsers, dependency
   parsers, LLM fallback candidate selection, component discovery, and
   doc-drift input preparation.
2. Add conservative path heuristics for common illustrative locations. Keep the
   list narrow, documented, and covered by positive and negative tests.
3. Add a `panopticon-ignore` hint with explicit file-level and
   declaration-level placement rules.
4. Apply the hint before deterministic parsing and before content is sent to an
   LLM. Ignored content must not persist in an index, component document, or
   drift finding.
5. Make ignored scope reviewable: tooling should report which path or
   declaration was excluded and whether the reason was a default heuristic or
   an explicit hint.
6. Add regression fixtures in which:
   - an example workflow resembles a real interface but is excluded;
   - a production path containing a similar word is not accidentally excluded;
   - an unconventional illustrative file is excluded by the hint;
   - mixed real and ignored declarations in one file preserve the real entry;
   - interface, dependency, component, and drift behavior agree.
7. Update the hint reference, extraction and drift skills, parser contribution
   guide, and normative interface/dependency/doc-generation specifications.

#### Step 5 — Where

- Shared deterministic scope module under `panopticon/`
- `panopticon/parsers/`
- `panopticon/extraction.py`
- `panopticon/dependency_extraction.py`
- `panopticon/drift.py`
- documentation/component discovery
- `.agents/skills/panopticon-*`
- `docs/hint-reference.md`
- `docs/parser-contribution.md`
- interface, dependency, and doc-generation specifications
- focused parser, extraction, drift, and docs tests

#### Step 5 — Pass

- All four consuming surfaces return the same decision for the same ignored
  path or declaration.
- Ignored content is not sent to an LLM and produces no persistent index or
  documentation artifact.
- Real production material in non-illustrative paths remains discoverable.

#### Step 5 — Fail

- If one subsystem disagrees, fix the shared deterministic policy or its
  adapter. Do not duplicate an ignore list in a skill prompt as the primary
  enforcement mechanism.

### 6. Adopt organization-scale interface names

Current guidance still favors locally meaningful functional names and rejects
owner prefixes. That permits generic names such as `message-bus`,
`config-store`, and `pprof-debug-endpoints` to collide or become ambiguous
after shard merge.

#### Step 6 — Do

1. Add normative naming rules for the merged organization scope:
   - qualify shared infrastructure with durable technology and function;
   - prefix repository-local service surfaces with their durable owner;
   - give distinct contracts on the same backend distinct names.
2. Require evidence from concrete configuration, ports, imports, or existing
   index entries rather than suggestive variable names.
3. Update both the interface-naming skill and interface-indexing specification.
   The skill alone is not a durable contract.
4. Add naming examples and counterexamples to the hint reference.
5. Add deterministic warnings for a small, reviewed set of known generic names;
   leave semantic renaming to the local agent and persisted hints.
6. Define an existing-instance migration:
   - inventory generic names in the compiled index;
   - update owning child hints and local shards;
   - merge child changes in a controlled sequence;
   - rebuild the compiled index;
   - use potential-name-collision findings as advisory evidence during the
     migration.
7. Add tests that prove distinct local resources do not fuse and that the same
   shared system still converges to one canonical name.

#### Step 6 — Where

- `.agents/skills/panopticon-interface-naming/SKILL.md`
- `.agents/skills/panopticon-index-schema/SKILL.md`
- `panopticon/naming.py`
- `panopticon/index.py`
- naming and merge tests
- `openspec/specs/interface-indexing/spec.md`
- `docs/hint-reference.md`
- `docs/setup-guide.md`

#### Step 6 — Pass

- New fixtures produce unambiguous organization-scale names.
- Two repositories referencing the same shared system converge.
- Two local surfaces with the same generic function remain distinct.
- The migration rebuild produces no unexplained same-name collision.

#### Step 6 — Fail

- If a rename is ambiguous, stop and ask which existing name is canonical.
  Never choose a cross-repository identifier from aesthetics or local
  consistency alone.

### 7. Turn the four gates into the supported operating process

The setup guide covers provider setup but does not yet document private
reusable-workflow access, zero-job diagnosis, caller OIDC identity, or
organization-specific per-child identity provisioning as one ordered process.
The Bedrock workflow also lacks a caller-level recovery step for credential
action failure.

#### Step 7 — Do

1. Add a four-gate setup and troubleshooting sequence:
   - reusable-workflow access;
   - effective provider configuration;
   - caller-repository identity and credentials;
   - real provider request compatibility.
2. For each gate, document the observable symptom, authoritative evidence,
   ownership boundary, exact recovery action, and proof needed to advance.
3. Add a pre-child access check for private/internal instance workflows. Provide
   the GitHub UI URL shape and a deterministic API check without assuming the
   failure is missing YAML.
4. Explain that reusable workflow code does not transfer repository identity:
   the OIDC subject represents the caller, so an organization may need to
   provision every child separately.
5. Bound an instance-managed credential step only where the workflow engine
   supports the bound. Put failure and timeout guidance in a later caller
   workflow step using an `always()`-style condition, outside the composite
   action that may be cancelled.
6. Make every failure summary answer: which gate failed, which configured name
   or resource was expected, whether it is instance-wide or per child, where to
   fix it, and how to rerun.
7. Add a protected-path debt register to the setup guide:
   - reason and owner for each protected path;
   - upstream issue/change replacing the local customization;
   - last reconciliation result;
   - removal condition.
8. Fix adjacent setup-guide drift discovered during implementation, including
   duplicated wording and the outdated count of generated caller workflows.
9. Keep organization-specific links, account identifiers, role names, and model
   identifiers out of the public guide. The generic process may expose
   placeholders and concrete synthetic examples only.

#### Step 7 — Where

- `docs/setup-guide.md`
- `PANOPTICON.md`
- `panopticon/recovery.py`
- `.github/workflows/panopticon-pr-bedrock.yml`
- initialization and provider workflow summaries
- `docs/testing.md`
- provider, initialization, and PR-evaluation specifications

#### Step 7 — Pass

- A reader can identify the last proven gate without reading implementation
  source.
- Zero-job, missing-default, missing-caller-identity, credential timeout, and
  provider-request failures each point to distinct recovery instructions.
- Failure guidance appears even when the credential composite action fails or
  times out.
- Public docs contain no organization-sensitive values.

#### Step 7 — Fail

- If a recovery message can disappear with the component it diagnoses, move it
  to the next surviving boundary rather than adding more logging inside the
  failing component.

### 8. Generate the complex-organization instance template

Build a generic overlay for organizations that share Yotpo-like complexity
without copying Yotpo policy, identifiers, or private links. The overlay extends
an instance; it does not create a second provider runtime or allow child
repositories to inject arbitrary workflow steps.

#### Step 8 — Do

1. Define a versioned organization-profile schema with names and non-secret
   setup choices for:
   - provider and trusted credential mode;
   - instance token secret name;
   - model and request-budget variable names;
   - effective optional values and their default source;
   - shared credential action reference used by the instance-owned wrapper;
   - region output contract;
   - reusable-workflow access policy;
   - per-child identity provisioning instructions and diagnostic URL;
   - internal registries;
   - gating modes;
   - protected-path debt entries.
2. Add a deterministic generator that validates the profile before writing a
   reviewable instance overlay. It must never accept, print, or persist
   credential values.
3. Generate at least:
   - `panopticon.config.json` content;
   - the fixed-path instance credential wrapper;
   - required protected-path entries, with the fixed credential wrapper
     protected automatically in `instance-managed` mode;
   - an organization-specific setup checklist;
   - a child onboarding checklist ordered by the four gates;
   - recovery text for missing per-child identity;
   - a protected-path debt register.
4. Keep runtime trust closed:
   - the provider registry still selects a template-owned workflow;
   - the credential wrapper remains at the fixed reviewed path;
   - child configuration cannot select an arbitrary workflow or action;
   - generated callers continue mapping names explicitly and never use
     `secrets: inherit`.
5. Provide two synthetic example profiles:
   - direct GitHub OIDC with per-child roles;
   - instance-managed credentials using a shared organization action.
6. Add a validation command that fails on unresolved placeholders, unknown
   logical names, missing default sources, unprotected generated
   customizations, credential-looking values, or public artifacts containing
   organization-specific identifiers.
7. Add fixture tests that generate into a temporary instance, load the
   resulting provider contract, render child callers, run template sync
   protection checks, and exercise bootstrap without network calls.
8. Document the exact generate, review, and apply commands. Keep reference
   fields after the executable checklist.

#### Step 8 — Where

- New focused template assets under a descriptive `templates/` directory
- New deterministic generator/validator under `panopticon/`
- Synthetic profile fixtures under `tests/fixtures/`
- Generator and end-to-end tests
- `docs/complex-organization-template.md`
- `docs/setup-guide.md`
- provider, initialization, and tooling-currency specifications

#### Step 8 — Pass

- Both synthetic profiles generate valid, secret-free instance overlays.
- Re-running generation with the same profile is byte-for-byte idempotent.
- Generated configuration loads through the real provider-contract code.
- The instance-managed wrapper survives template sync without manually
  discovering a missing protected path.
- A generated child caller contains only explicit trusted mappings.
- The generated onboarding guide separates instance-wide access from per-child
  identity provisioning.

#### Step 8 — Fail

- If a profile requires arbitrary runtime workflow selection, add a reviewed
  built-in provider or credential-mode contract instead. Do not turn the
  organization template into workflow injection.

### 9. Roll out through boundary-specific gates

#### Step 9 — Do

1. Apply Steps 1–8 to a fresh sandbox instance generated from the public
   template, not to a hand-repaired historical copy.
2. Create or select one sandbox child and record the result at each gate:
   - instance workflow access check;
   - reusable workflow job creation;
   - effective configuration validation;
   - caller permission and OIDC identity;
   - credential setup;
   - SDK capability preflight;
   - real structured inference;
   - doc-drift and index-currency checks;
   - branch-state push and merge synchronization.
3. Exercise local bootstrap, local sync, resource-sync pull request creation,
   finalization reporting, and a compiled-index rebuild.
4. Test one expected failure per gate and confirm its recovery message survives
   at the correct boundary.
5. Remove temporary downstream protections only after the equivalent upstream
   file is synced and the sandbox child proves the upstream behavior.
6. Record operational proof separately from local and static verification.

#### Step 9 — Where

- Sandbox instance generated from the new complex-organization template
- Sandbox child repository
- GitHub Actions run summaries
- Generated initialization report
- Instance compiled indexes and organization architecture document

#### Step 9 — Pass

- The sandbox child completes the entire sequence with one real provider
  inference and one successful instance sync.
- Every injected failure names the correct gate and exact recovery action.
- No CI-only module exists in the child after bootstrap or sync.
- No required configuration is falsely reported missing.
- No local protected workflow remains solely to carry a now-upstream fix.

#### Step 9 — Fail

- Stop at the failed boundary and retain the last proven status. Do not describe
  the rollout as complete, and do not change a later layer until the current
  gate passes.

## Permission and access checks

Run these checks before the first sandbox child write:

1. Confirm the sandbox instance permits the intended organization repositories
   to call its reusable workflows.
2. Confirm the instance-token secret is visible to the sandbox child and has
   the documented instance-repository permissions.
3. For direct OIDC, confirm the caller has `id-token: write`, the OIDC trust
   recognizes the child repository, and provider permissions cover both the
   selected inference profile and underlying model when applicable.
4. For instance-managed credentials, confirm the fixed credential action exists
   and its generated wrapper is protected.
5. Confirm the sandbox identity has permission to push branch state, update the
   compiled instance index, and create or update conflict issues where the
   existing workflow requires it.

After the first successful write, verify:

1. The child branch appears only at the expected `{repo}/{branch}` instance
   branch.
2. A merge replaces only the owning child's shard and rebuilds the compiled
   index.
3. The generated organization document is rebuilt from the compiled index.
4. No credential value appears in generated configuration, reports, workflow
   output, or template fixtures.

## Reference: priority and issue map

| Priority | Lesson or issue | Verified current state | Planned resolution |
| --- | --- | --- | --- |
| P0 | #14 workflow copy/paste | Bedrock references undeclared LiteLLM input and secret names | Step 1 |
| P0 | #19 provider API drift | Bedrock always sends `temperature` | Step 2 |
| P0 | #13 sync boundary | Sync copies the complete package and tests require `llm.py` | Step 3 |
| P1 | #18 effective defaults | Provider contracts have no required/optional semantics | Step 4 |
| P1 | #11 illustrative code | Shared file iteration does not exclude common illustrative paths | Step 5 |
| P1 | #12 deterministic override | No `panopticon-ignore` hint exists | Step 5 |
| P1 | #16 global identity | Naming guidance remains local-function-first | Step 6 |
| P1 | #15 onboarding complexity | Generic setup omits the complete ordered access/identity gate model | Steps 7–8 |
| Preserve | Provider abstraction | LiteLLM, OpenAI, and Bedrock adapters exist behind the shared client | Step 0 regression coverage |
| Preserve | OIDC caller permission | Generated Bedrock callers include `id-token: write` | Step 0 regression coverage |
| Preserve | Python isolation | Bedrock workflow uses isolated Python and a pinned SDK | Step 0 regression coverage |
| Preserve | Runtime preflight | Provider preflight exists before LLM checks | Step 0 regression coverage |
| Preserve | Init dependency order | `panopticon-init` includes dependency naming and extraction | Step 0 regression coverage |

## Reference: complex-organization template contract

The first reusable template targets the complexity class, not one organization:

| Concern | Template behavior | Organization supplies |
| --- | --- | --- |
| Provider workflow | Selects a built-in trusted provider workflow | Provider choice |
| Credentials | Uses direct OIDC or the fixed instance wrapper | Shared action reference or role settings |
| Secret indirection | Maps a validated Actions secret name | Secret name and value in organization settings |
| Defaults | Records effective optionality and default source | Non-secret default source |
| Child identity | Produces an ordered provisioning check | Organization-specific provisioning URL or command |
| Workflow access | Produces a pre-child access check | Desired repository access scope |
| Sync ownership | Uses the instance-published local-tooling manifest | No child allowlist |
| Customization safety | Generates protection and a debt register | Reason and removal condition |
| Gating | Uses existing per-check modes | Advisory/blocking choices |
| Documentation | Generates the four-gate onboarding runbook | Organization-neutral labels and synthetic examples |

## Decisions

- Runtime blockers precede semantic quality changes because they prevent any
  real Bedrock evaluation.
- The instance is the authority for the current local-tooling manifest; the
  child does not carry an independently stale allowlist.
- `panopticon-ignore` is deterministic and shared across parsers and LLM input
  preparation.
- Organization-scale naming is normative in the specification and operational
  in the skill.
- The complex-organization template is an instance overlay generated from a
  validated profile, not a new provider fork and not a child workflow-injection
  mechanism.
- Real child execution is required to claim operational proof for access,
  identity, credentials, and provider compatibility.

## Assumptions

- The first complex-organization template supports all built-in providers but
  gives the richest example to Bedrock with instance-managed credentials,
  because that path exercises every observed complexity.
- The template contains only synthetic examples. Existing Yotpo account IDs,
  role names, model profile identifiers, repository names, internal URLs, and
  run links are source evidence only and are not reusable template content.
- Unknown extra child tooling files are reported but not deleted because the
  template cannot prove their ownership.
- Potential same-name collision detection remains advisory evidence during
  naming migration; it is not a substitute for canonical-name judgment.

## Open questions before implementation

These decisions do not block this planning document, but they must be resolved
in the relevant OpenSpec design before code is written:

1. What stable path and schema name should the local-tooling manifest use?
2. Should effective provider defaults be stored as non-secret instance
   configuration, resolved by a fixed instance action, or supported through
   both trusted sources?
3. Which exact path components belong in the conservative illustrative-material
   default set without excluding legitimate production layouts?
4. Should the complex-organization profile be JSON, YAML, or a guided
   configuration workflow input that persists the same validated schema?
5. Which public, organization-neutral failure fields are safe to render into a
   generated child onboarding guide when an organization supplies a private
   provisioning URL?

The next action is to create the Step 1 OpenSpec change for reusable-workflow
contract validation and the Bedrock workflow cleanup.
