# Bedrock Converse Request Shape Design

## Context

The provider-neutral client calls each adapter with a `temperature` argument.
The Bedrock adapter currently forwards it as `inferenceConfig.temperature`, but
the configured Claude Converse model rejects that field. The resulting request
failure occurs after credentials and workflow configuration have succeeded.

## Goals / Non-Goals

**Goals:**

- Send a minimal, supported Bedrock Converse request.
- Preserve the shared adapter method signature and retry behavior.
- Assert the complete native request shape in unit tests.

**Non-Goals:**

- Add a Bedrock-specific temperature setting or model capability registry.
- Alter LiteLLM or OpenAI request bodies.
- Change Bedrock authentication, SDK pinning, or error classification.

## Decisions

### Omit inference configuration entirely

The Bedrock adapter will accept the shared `temperature` parameter to preserve
the provider-neutral caller interface, but will not include `inferenceConfig`
in Converse requests. This follows the plan's safe default: no optional native
parameter is sent until its support is explicitly confirmed and covered by a
provider-specific test.

Adding a configurable Bedrock temperature would require a capability contract
for model-specific support and is out of scope. Forwarding the existing shared
argument is rejected because it is the observed compatibility failure.

## Risks / Trade-offs

- [A future supported model could benefit from temperature control] → Add an
  explicit, model-capability-backed contract and regression coverage before
  sending the field.
- [Callers expect the supplied temperature to affect Bedrock output] → Retain
  the method signature but document and test that the current Bedrock request
  intentionally omits the field.

## Migration Plan

1. Remove the native inference configuration from the adapter and update its
   request-shape test.
2. Run the focused adapter tests and the complete suite.
3. Publish through the normal template-sync path; no instance configuration or
   data migration is required.

## Open Questions

None.
