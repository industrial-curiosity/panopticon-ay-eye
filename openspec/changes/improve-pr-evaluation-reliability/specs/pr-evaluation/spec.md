# PR evaluation delta

## ADDED Requirements

### Requirement: Doc-drift context is relevance-first and conservative

For a behavior-bearing pull-request diff, doc drift SHALL exclude the deterministically rendered `interfaces.md` document from LLM context. It SHALL include `architecture.md` and `operations.md`. It SHALL include a component document when that document explicitly names a behavior-bearing changed path. If any behavior-bearing changed path has no deterministic component-document match, doc drift SHALL include every component document that fits within its existing bounded input budget. The check report SHALL state the context-selection mode and selected documentation paths.

#### Scenario: Changed path is explicitly documented by one component

- **GIVEN** a behavior-bearing changed path is explicitly named by one component document
- **WHEN** doc drift prepares its LLM context
- **THEN** it includes architecture, operations, and that component document, excludes deterministic interfaces, and reports that it used targeted component context

#### Scenario: Changed path has no deterministic component-document match

- **GIVEN** at least one behavior-bearing changed path is not explicitly named by any component document
- **WHEN** doc drift prepares its LLM context
- **THEN** it includes architecture, operations, and every component document within the existing byte budget and reports that it used the conservative fallback

#### Scenario: No behavior-bearing change

- **WHEN** a PR changes no behavior-bearing path
- **THEN** doc drift returns its clean deterministic verdict without creating an LLM request or request diagnostics

## MODIFIED Requirements

### Requirement: CI checks distinguish operational failure from a business verdict by exit code

Every LLM-backed PR-evaluation check (doc-drift, index-currency) SHALL use a fixed exit-code contract: `0` means the check ran successfully and found no issue; `2` means the check ran successfully and found an actionable issue (stale docs, a stale index); any other exit code — including whatever an uncaught exception produces by default in the check's language runtime — SHALL be treated by the calling workflow as an operational failure: the check did not complete and its outcome is unknown, never a verdict. `1` SHALL NOT be used to mean either outcome, since it collides with the exit code most language runtimes (including Python) already use by default for any uncaught exception, making a genuine crash indistinguishable from a deliberate "stale" result. This mirrors the pre-merge-simulation check's existing exit-code convention (`0`/`2`/anything-else), which does not have this collision.

Every code path that can produce an operational failure — a malformed LLM response, a missing or unreachable endpoint, or any other exception raised while producing the verdict — SHALL be caught explicitly and turned into a non-`0`/non-`2` exit paired with a clear plain-text diagnostic and an operational-failure report section. The check CLI and its wrapper step SHALL NOT emit GitHub `::error::` workflow commands for that failure. After all independent checks and the combined report have run, the final gating step SHALL emit exactly one Panopticon-authored `::error::` annotation for each operationally failed check and fail the workflow. GitHub-generated failed-step status is outside this requirement.

#### Scenario: Malformed LLM response is an operational failure, not a stale verdict

- **GIVEN** the LLM endpoint returns a response that fails to parse as the expected verdict JSON
- **WHEN** the doc-drift or index-currency check runs
- **THEN** the check exits with a code that is neither `0` nor `2`, writes an operational-failure report rather than a real stale finding, and the final gate emits one Panopticon-authored `::error::` annotation identifying the failed check

#### Scenario: Genuine stale verdict still exits with the reserved code

- **GIVEN** the LLM endpoint returns a well-formed verdict indicating stale docs or a stale index
- **WHEN** the check runs
- **THEN** it exits `2`, the workflow proceeds to the combined report, and gating applies normally
