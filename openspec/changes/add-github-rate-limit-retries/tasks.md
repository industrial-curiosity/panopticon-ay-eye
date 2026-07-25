# Tasks: GitHub API rate-limit retries

## 1. Add rate-limit-aware GitHub retrieval

- [x] 1.1 Add a stdlib-only classifier and delay calculation for GitHub rate-limit responses, preserving immediate failures for non-rate-limit authorization and missing-resource errors.
- [x] 1.2 Apply the retry policy and safe retry-progress messages to the public `install.py` launcher without weakening its redacted error handling.
- [x] 1.3 Apply the mirrored retry policy to `panopticon.bootstrap` and vendored `panopticon.sync` without introducing an import dependency between them.

## 2. Verify recovery behavior

- [x] 2.1 Add launcher tests for reset-header, `Retry-After`, and genuine forbidden-response behavior.
- [x] 2.2 Extend bootstrap and sync tests for rate-limit classification, header-derived waits, fallback backoff, exhausted retries, and token-safe progress output.
- [x] 2.3 Run focused launcher, bootstrap, and sync tests, then the full Python suite.

## 3. Remove the initialization ordering deadlock

- [x] 3.1 Add a pre-finalization context derivation path for documentation generation and organization-diagram links without creating `panopticon/config.json` early.
- [x] 3.2 Update `/panopticon-init` and documentation-generation guidance so normal initialization continues directly from index work through finalization with no user-mediated phase transition.
- [x] 3.3 Add regression coverage for fresh and checkpoint-resumed initialization, plus missing caller-workflow recovery guidance.

## 4. Document the recovery contract

- [x] 4.1 Update setup and testing documentation to explain automatic rate-limit recovery and retain authentication as the preferred path.
- [x] 4.2 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
