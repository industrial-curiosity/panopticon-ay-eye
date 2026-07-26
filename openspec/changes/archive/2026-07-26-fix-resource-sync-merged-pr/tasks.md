# Fix resource-sync merged PR reuse tasks

## 1. Workflow lifecycle

- [x] 1.1 Restrict the shared resource-sync workflow's reusable pull request
  lookup to open automation-owned pull requests for the child default branch.
- [x] 1.2 Create a new pull request when no open automation-owned pull request
  exists, including after the prior pull request was merged or closed.

## 2. Verification

- [x] 2.1 Add or update a workflow regression test that distinguishes an open
  pull request from a merged or closed pull request.
- [x] 2.2 Run the focused workflow test and the repository test suite.

## 3. Documentation

- [x] 3.1 Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes introduced by this change.
