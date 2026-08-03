# Dependency indexing specification delta

## MODIFIED Requirements

### Requirement: Hint annotations and LLM extraction fallback

Dependency naming and internal/external judgments SHALL be persisted as hints, mirroring the
interface-indexing capability's hint contract: `panopticon-dependency &lt;name&gt;`-prefixed comments
pin a candidate's canonical name and internal status. Extraction SHALL honor hints before
structural rules, registry-host matching, or instance cross-reference. Before deterministic parsing
or LLM fallback, dependency extraction SHALL apply the shared analysis-scope policy, including
explicit ignore annotations. For candidates no layer resolves, extraction SHALL fall back to the
LLM locally through the user's agent and in CI through the agent runtime scoped to the diff, tagging
entries `"extracted_by": "llm"` and recommending a deterministic parser when LLM extraction
recurs. A CI evaluation that cannot resolve a candidate from any layer SHALL fail with an
instruction to add a `panopticon-dependency` hint, matching the interface-indexing capability's CI
behavior.

#### Scenario: Hint pins a candidate the other layers miss

- **WHEN** a source file carries `# panopticon-dependency internal-metrics-lib` next to a dependency declaration that no structural, registry, or cross-reference layer resolved
- **THEN** extraction uses `internal-metrics-lib` as the canonical name with no LLM judgment

#### Scenario: Non-manifest declaration caught by LLM fallback

- **WHEN** a dependency is declared outside any manifest file and no parser covers that pattern
- **THEN** LLM extraction may emit an entry tagged `"extracted_by": "llm"`, and the workflow summary recommends a deterministic parser for that pattern

#### Scenario: CI cannot resolve a candidate

- **WHEN** a PR changes a dependency candidate that no layer can resolve as internal or external
- **THEN** the check fails, instructing the developer to add a `panopticon-dependency` hint

#### Scenario: Internal dependency in illustrative material is excluded

- **GIVEN** an internal dependency declaration or import is under `samples/` or `fixtures/`
- **WHEN** dependency extraction runs
- **THEN** it SHALL neither index nor send that dependency to the LLM, and its summary SHALL report
  the illustrative-directory exclusion
