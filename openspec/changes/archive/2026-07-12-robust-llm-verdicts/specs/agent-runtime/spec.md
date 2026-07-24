# Agent Runtime Spec

## ADDED Requirements

### Requirement: Structured-response retry for non-compliant model output

The runtime SHALL, for any CI check that requires a structured (JSON) response —
the doc-drift,
index-currency, and interface-extraction checks — use a single shared runtime
method that validates
the response against the check's expected shape and, on a parse or validation
failure, retries with
a corrective message appended to the conversation before failing loudly. The
retry budget SHALL be
small and bounded; exhausting it SHALL raise the same loud, exit-code-visible
operational failure
this runtime already guarantees for missing configuration (see "Fail loudly on
missing
requirements") — a check MUST NOT silently accept a response that failed
validation, and MUST NOT
retry indefinitely. This behavior SHALL work against any litellm-compatible
endpoint with no
provider-specific request parameters, consistent with "Provider-agnostic LLM
configuration for CI."

#### Scenario: Non-compliant response is corrected on retry

- **GIVEN** a check requests a structured JSON response and the model's first
  response is prose
  that fails to parse as JSON
- **WHEN** the runtime retries with a corrective message
- **THEN** a second, compliant response is parsed and validated successfully,
  and the check
  proceeds normally with no operational failure

#### Scenario: Persistently non-compliant response fails loudly after the retry budget is exhausted

- **GIVEN** a model's response fails to parse or validate on every attempt
- **WHEN** the runtime exhausts its bounded retry budget
- **THEN** the check fails with an operational-failure error identifying which
  check it was and
  that the response was not the expected shape — the check never silently
  proceeds with malformed
  or partial data

#### Scenario: A validation failure is corrected on retry, not only a syntactic parse failure

- **GIVEN** a model's response is syntactically valid JSON but is missing a
  required field or has
  a field of the wrong type
- **WHEN** the runtime retries with a corrective message describing the specific
  validation problem
- **THEN** the retry can succeed with a shape-correct response, the same
  recovery path as a
  syntactic parse failure

#### Scenario: No provider-specific structured-output parameters are required

- **WHEN** the runtime sends a structured-response request, including any
  corrective retry
- **THEN** the request payload uses the same OpenAI-compatible
  `/chat/completions` shape as any
  other request — no `response_format` or other provider-specific field is
  required for retry and
  validation to work
