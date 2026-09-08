# Implementation tasks

## 1. Template sync branch selection and summary

- [ ] 1.1 Add the optional `template_ref` workflow-dispatch and reusable-workflow contract, preserving `main` as the compatibility default.
- [ ] 1.2 Fetch, merge, report, and generate local recovery instructions using the validated selected template ref.
- [ ] 1.3 Append the selected ref and post-merge changed repository-relative paths, or an explicit no-change result, to the template-sync Actions summary.
- [ ] 1.4 Extend template-sync workflow contract tests for named refs, default compatibility, recovery text, and changed-path summaries.

## 2. Doc-drift debug visibility

- [ ] 2.1 Add an opt-in, secret-safe debug output mode to `panopticon.drift` for scope filtering, planning, batch assignments, and evaluation progress.
- [ ] 2.2 Enable debug mode in the LiteLLM, OpenAI, and Bedrock reusable PR workflows without adding the trace to reports or summaries.
- [ ] 2.3 Add Python and workflow-contract tests that verify safe debug events, per-batch visibility, all provider invocations, and the absence of prompt or credential content.

## 3. Validation and documentation

- [ ] 3.1 Run the affected unit and workflow-contract tests, then the repository's required validation suite.
- [ ] 3.2 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
