# Implementation tasks

## 1. Shared scope policy

- [x] 1.1 Add a stdlib-only `panopticon.scope` module that classifies exact illustrative directory components, explicit file hints, and explicit declaration hints with stable reasons.
- [x] 1.2 Add scope unit tests for every excluded directory name, case-insensitive exact-component matching, non-matching production paths, header placement, and declaration placement.
- [x] 1.3 Add scope reporting helpers that identify excluded repository-relative paths or declaration locations without exposing unrelated file content.

## 2. Interface and dependency extraction

- [x] 2.1 Apply shared scope filtering in `panopticon.parsers.iter_files` before parser detection and extraction, and expose exclusions to extraction summaries.
- [x] 2.2 Update built-in interface parsers and the shared interface extraction driver to retain declaration line metadata, filter ignored candidates, and redact ignored fallback content before LLM requests.
- [x] 2.3 Update dependency parsers and the dependency extraction driver with the same candidate filtering, fallback redaction, and summary reporting.
- [x] 2.4 Add interface and dependency regression fixtures covering excluded examples, samples and fixtures containing internal dependencies, production near-matches, file hints, mixed declarations, and no-LLM-input guarantees.

## 3. Documentation and drift integration

- [x] 3.1 Apply the shared policy to doc-drift behavior-path selection and diff/prompt preparation; return the existing clean verdict without an LLM call when scope removes all behavior-bearing content.
- [x] 3.2 Add a managed `## Panopticon analysis scope` section to `operations.md` generation and validation, listing actual excluded directories, default rules, and explicit hint syntax.
- [x] 3.3 Add the stable `operations.md#panopticon-analysis-scope` link directly below the architecture diagram and retain the existing org-diagram link.
- [x] 3.4 Add doc, drift, and architecture-template tests for the managed section, directory inventory, link placement, and ignored-only pull requests.

## 4. Distribution, documentation, and verification

- [x] 4.1 Add `scope.py` to the child-safe local-tooling manifest and verify bootstrap and sync deliver it atomically.
- [x] 4.2 Update `docs/hint-reference.md`, `docs/parser-contribution.md`, extraction and doc-drift skills, and all affected OpenSpec specifications with the scope contract and reporting behavior.
- [x] 4.3 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
- [x] 4.4 Run focused scope, parser, extraction, dependency, docs, and drift tests; the full Python suite; reusable-workflow validation; strict OpenSpec validation; and Markdown structure checks.
