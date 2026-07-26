# Resource-sync pull request lifecycle design

## Context

The shared child resource-sync workflow uses a fixed automation branch and
pushes refreshed resources before choosing a pull request. Branch-based pull
request lookup can resolve a historical merged or closed pull request unless
the lookup explicitly limits the lifecycle state.

## Goals / Non-Goals

**Goals:**

- Reuse the automation branch while reusing only an open review pull request.
- Create a fresh review pull request after the prior one is merged or closed.
- Make the lifecycle rule observable in the workflow contract test and user
  documentation.

**Non-Goals:**

- Changing the automation branch name, pull request title, or permissions.
- Reopening merged or closed pull requests.
- Changing the resource-sync behavior when managed resources are current.

## Decisions

### Query only open pull requests

The workflow queries pull requests by its fixed head branch, the child default
branch, and the `open` state. An empty result creates a pull request.

This preserves the existing single active automation review while making a
historical pull request ineligible for update. Inspecting all pull requests and
filtering after selection is rejected because it can accidentally choose a
merged or closed result.

### Keep the automation branch fixed

The workflow continues force-with-lease pushes to its existing automation
branch. A new branch per refresh is rejected because it would create avoidable
branch churn and does not solve the pull request lifecycle distinction.

## Risks / Trade-offs

- A historical pull request remains discoverable through GitHub history but is
  intentionally not reused → the state-qualified lookup excludes it.
- A new pull request is created after a closed pull request → this preserves a
  reviewable change rather than reopening a decision that was already closed.

## Migration Plan

1. Update the shared workflow and its contract test.
2. Update the tooling-currency specification and documentation.
3. Publish the workflow change through the instance repository so child callers
   resolve the corrected reusable workflow.

Rollback restores the previous shared workflow revision; no child-repository
data migration is required.

## Open Questions

None.
