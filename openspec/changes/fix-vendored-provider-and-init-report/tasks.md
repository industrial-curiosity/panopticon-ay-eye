# Tasks: vendored provider tooling and initialization reports

## 1. Restore complete local tooling vendoring

- [ ] 1.1 Add `providers.py` to the mirrored bootstrap and sync local-tooling module lists, and update their dependency-boundary comments.
- [ ] 1.2 Extend bootstrap and sync regression tests to prove a new or older child receives `providers.py` and local commands can import it.

## 2. Produce durable initialization reports

- [ ] 2.1 Add report assembly and atomic write behavior to `panopticon.init_repo` so every finalization attempt creates `panopticon-initialization-report.md` before exit.
- [ ] 2.2 Classify each initialization finding by template/tooling, child repository, or organization configuration, with an affected location and a concise recovery action while excluding credential values.
- [ ] 2.3 Update finalization CLI output to state the report location and outcome without duplicating the full report.
- [ ] 2.4 Add tests for failed validation, unavailable organization verification, clean success, and re-finalization report replacement.

## 3. Document and verify the change

- [ ] 3.1 Correct vendored-tooling documentation and explain how users read and refresh the initialization report.
- [ ] 3.2 Run focused bootstrap, sync, and initialization tests, then the full Python test suite and Markdown linting.
- [ ] 3.3 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
