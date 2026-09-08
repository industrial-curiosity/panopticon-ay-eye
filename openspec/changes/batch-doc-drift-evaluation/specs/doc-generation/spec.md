# Doc-generation changes

## ADDED Requirements

### Requirement: Doc-vs-code drift SHALL aggregate planned batch results

For a pull request with behavior-bearing product changes, doc drift SHALL use
validated planned batches instead of one full-diff prompt. It SHALL aggregate
all batch stale reasons into one doc-drift result, preserve the source-file
evidence and remediation contract for every stale document, and return clean
only when every evaluated batch is clean.

#### Scenario: All planned batches are clean

- **WHEN** every planned batch has documentation consistent with its changed
  product behavior
- **THEN** doc drift returns its clean verdict after evaluating every batch
