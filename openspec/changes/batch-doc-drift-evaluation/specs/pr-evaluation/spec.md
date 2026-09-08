# PR-evaluation changes

## ADDED Requirements

### Requirement: Planned doc-drift batching SHALL preserve independent PR evaluation

The PR workflow SHALL treat a doc-drift planning or batch-evaluation failure as
the existing doc-drift operational failure. It SHALL continue to run
index-currency and pre-merge simulation, include each check's actual status in
the combined report, and apply the existing final-gate policy after all
independent checks complete.

#### Scenario: Doc-drift batch evaluation times out

- **WHEN** doc drift reports a timed-out evaluation batch
- **THEN** index-currency and pre-merge simulation still run and the final gate
  fails with the doc-drift operational-failure annotation
