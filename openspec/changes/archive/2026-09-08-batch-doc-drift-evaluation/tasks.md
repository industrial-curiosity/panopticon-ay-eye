# Implementation tasks

## 1. Deterministic scope and batch planning

- [x] 1.1 Extend doc-drift path classification so `panopticon/`, `.github/`, and `.agents/` are excluded as managed metadata before behavior-path selection.
- [x] 1.2 Add a dedicated doc-drift batch-planning skill and stdlib-only planning/validation helpers that assign every retained changed path exactly once to minimal batches and known documentation paths.
- [x] 1.3 Add hermetic unit tests for metadata-only clean verdicts, valid minimal batches, and invalid planner assignments.

## 2. Isolated evaluation and reports

- [x] 2.1 Evaluate validated batches with only their patch and documentation contents, aggregate stale reasons and diagnostics, and preserve the existing exit-code contract.
- [x] 2.2 Add stage-aware doc-drift operational-failure formatting for planning and evaluation timeouts, including safe path and byte details plus PR-size and timeout remedies.
- [x] 2.3 Add hermetic tests for clean and stale aggregate results, evaluator isolation, immediate timeout failure without later-batch execution, and secret-safe recovery output.

## 3. Workflow and regression validation

- [x] 3.1 Verify reusable-workflow wrappers and final gating retain independent index-currency and pre-merge execution after a doc-drift batch failure.
- [x] 3.2 Add a regression fixture matching the metadata-heavy child-reinitialization PR so doc drift makes no LLM request.
- [x] 3.3 Run the focused doc-drift, report, and provider-workflow tests, then the complete test suite.

## 4. Documentation

- [x] 4.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
