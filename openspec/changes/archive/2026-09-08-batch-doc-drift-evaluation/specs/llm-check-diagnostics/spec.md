# LLM check diagnostics changes

## ADDED Requirements

### Requirement: Doc-drift timeout reports SHALL include batch recovery guidance

The doc-drift operational-failure report SHALL identify the failed stage, safe
selected path names, input byte count, attempt count, elapsed duration, and
timeout outcome when planning or batch evaluation times out. It SHALL instruct
the developer to reduce or split the pull request and to consider increasing
`PANOPTICON_LLM_TIMEOUT_SECONDS` within its supported range. The report SHALL
not expose endpoint URLs, credentials, prompt content, documentation content,
or resolved secret values.

#### Scenario: Planner times out

- **WHEN** the doc-drift batch planner exhausts its configured attempts
- **THEN** the report identifies planning as the failed stage and gives both
  PR-size and timeout-configuration recovery actions
