# Add shared child resource sync

## Why

Child repositories can refresh Panopticon skills and vendored tooling only by
running a local command. Organizations need a shared GitHub Actions path that
keeps those resources current without rerunning bootstrap and gives maintainers
a reviewable pull request rather than an unattended default-branch push.

## What Changes

- Add a minimal, bootstrapped child workflow that calls template-owned shared
  resource-sync logic.
- Refresh the child’s managed skills and vendored local tooling from its
  configured instance repository.
- Create or update a child-repository pull request only when resources differ.
- Use the existing instance-read credential only for fetching private instance
  resources; use the child workflow token for the child-repository pull request.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `tooling-currency`: Add an Actions-based, reviewable path for synchronizing
  child skills and local tooling.
- `repo-initialization`: Wire the stable child resource-sync caller during
  bootstrap without requiring a later installer run.

## Impact

- Child caller workflow written by bootstrap
- Template-owned reusable GitHub Actions workflow and resource-sync tests
- Setup and getting-started guidance for the manual update path
