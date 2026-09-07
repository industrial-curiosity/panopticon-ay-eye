# LLM check diagnostics

## Purpose

Define safe request diagnostics published by LLM-backed CI checks.

## Requirements

### Requirement: LLM-backed CI checks publish safe request diagnostics

The provider-neutral LLM runtime SHALL make one diagnostic record available to
each LLM-backed CI check after its request attempt sequence. The record SHALL
include the provider identifier, model identifier, request input byte count,
transport-attempt count, elapsed duration, and outcome class. The check's
report SHALL include the record for a completed request and SHALL include
available fields when a request fails. Diagnostics SHALL NOT include endpoint
URLs, API keys, secret names or values, prompt content, documentation content,
response content, or resolved configuration values.

#### Scenario: Timed-out doc-drift request

- **GIVEN** the configured provider exhausts its transport attempts while doc
  drift is evaluating a behavior-bearing change
- **WHEN** doc drift writes its operational-failure report
- **THEN** the report identifies the failed request's provider, model, input
  byte count, transport-attempt count, elapsed duration, and timeout outcome
  without exposing the endpoint or prompt content

#### Scenario: Configuration fails before a request

- **GIVEN** an LLM-backed check cannot construct a configured client
- **WHEN** it writes its operational-failure report
- **THEN** it retains the configuration recovery message and states that
  request diagnostics are unavailable because no request was made

#### Scenario: Successful structured request

- **GIVEN** an LLM-backed check receives a valid structured response
- **WHEN** it writes its check report
- **THEN** the report includes safe diagnostics for the completed request and
  does not include the request or response content
