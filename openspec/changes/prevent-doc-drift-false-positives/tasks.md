## 1. Evidence-backed drift evaluation

- [x] 1.1 Classify PR diffs in `panopticon.drift` and return a clean verdict without an LLM request when only documentation, skills, OpenSpec artifacts, changelogs, or tests changed.
- [x] 1.2 Extend stale-verdict validation so each finding has a non-empty update and evidence tied to a changed behavior-bearing file; route invalid findings through the existing operational-failure contract.
- [x] 1.3 Update the doc-drift skill to require a clean verdict for adequately updated docs and to prohibit unsupported or contradictory stale reasons.

## 2. Regression coverage

- [x] 2.1 Add unit tests for PR #6's guidance-plus-architecture-doc pattern, proving it returns clean without calling the LLM.
- [x] 2.2 Add unit tests for evidence-backed genuine stale findings and invalid empty, contradictory, or untraceable findings, including operational-failure reporting.
- [x] 2.3 Verify the LiteLLM, OpenAI, and Bedrock reusable workflows continue to distinguish validated stale verdicts from invalid-response operational failures.

## 3. Documentation and verification

- [x] 3.1 Update `docs/testing.md` for the expanded doc-drift regression coverage, run the relevant suite, and run `openspec validate prevent-doc-drift-false-positives --strict`.
- [x] Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
