## 1. Shared resource-sync workflow

- [x] 1.1 Add the template-owned reusable child resource-sync workflow with
  default-branch enforcement and explicitly separated instance-read and
  child-repository write credentials.
- [x] 1.2 Make the shared workflow run the existing local sync behavior and
  create or update one automation-owned pull request only when managed
  resources changed.
- [x] 1.3 Add the minimal manual child caller for the shared workflow with only
  the required permissions and explicit secret mapping.

## 2. Bootstrap integration

- [x] 2.1 Extend bootstrap workflow wiring so new and refreshed child repos
  receive the stable resource-sync caller without reinitialization.
- [x] 2.2 Update bootstrap tests for the added caller and its idempotent wiring.

## 3. Workflow regression coverage

- [x] 3.1 Add reusable-workflow contract tests for default-branch credential
  protection, no-change behavior, and create-or-update PR behavior.
- [x] 3.2 Verify the resource-sync workflow remains compatible with private
  instance repositories and does not broaden the instance-read secret's scope.

## 4. Documentation and verification

- [x] 4.1 Update setup and getting-started guidance with the manual
  resource-sync workflow and its reviewable-PR behavior; run the relevant test
  suite and strict OpenSpec validation.
- [x] Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
