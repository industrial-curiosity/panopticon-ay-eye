# Master Sync Spec

## ADDED Requirements

### Requirement: Org diagram rebuild on merge to main

When a child repo merges to its default branch, the sync workflow SHALL
deterministically rebuild the org
diagram document (architecture-diagrams capability) from the freshly compiled
index, immediately after
`compile_index()` produces the new compiled state, and include the result in the
same commit as the compiled
index rebuild. This rebuild SHALL require no LLM call and no dependency on any
child repo having a diagram
section yet — it is derived entirely from the compiled index's
`owner`/`producer`/`consumer` data.

#### Scenario: Merge to main rebuilds the org diagram

- **WHEN** a PR merges to main in an initialized child repo and the merge sync
  workflow runs
- **THEN** the instance repo's default branch contains an org diagram document
  reflecting the freshly
  compiled index, committed alongside the compiled index itself

#### Scenario: Org diagram rebuild does not depend on per-repo diagrams existing

- **WHEN** a child repo has no `## Architecture diagram` section in its own
  `architecture.md`
- **THEN** the org diagram rebuild still succeeds, using only that repo's
  compiled-index entries; the repo's
  section (if it has external interfaces) links to `docs/{repo}/architecture.md`
  regardless of whether that
  file itself contains a diagram section
