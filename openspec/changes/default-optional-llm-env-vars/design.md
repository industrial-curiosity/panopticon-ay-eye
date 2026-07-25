# Default optional LLM environment variables design

## Context

The reusable LiteLLM and Bedrock PR workflows accept optional request-budget
inputs. Their job-level environments provide the documented defaults, but
individual LLM check steps currently map those same inputs directly. When an
organization does not define one of the optional Actions variables, GitHub
Actions supplies an empty value to those step environments, and the Python
runtime correctly rejects that empty string as an invalid explicit override.

## Goals / Non-Goals

**Goals:**

- Apply the existing request-budget defaults consistently at each workflow
  environment boundary that supplies variables to LLM code.
- Preserve the configured-valid-value and invalid-value behavior already
  defined for both providers.
- Cover absent values for timeout, transport attempts, and correction attempts
  in structural workflow tests.

**Non-Goals:**

- Change the documented defaults, allowed ranges, or retry semantics.
- Treat required provider credentials or provider-specific configuration as
  optional.
- Change model configuration, whose requiredness differs between providers.

## Decisions

### Default at each step environment boundary

Each LLM-invoking step SHALL use the same GitHub Actions expression as the job
environment for all optional request-budget inputs. This keeps the Python
runtime's absent-value behavior intact while preventing workflow wiring from
turning absence into an empty-string override.

Applying the fallback only in Python was considered but rejected because the
runtime cannot distinguish an absent input from an explicitly mapped blank
value after the workflow has set the environment variable. Applying defaults
only to the job environment was also rejected because step-level `env` blocks
override that environment.

### Symmetric provider coverage

The LiteLLM and Bedrock reusable workflows SHALL use identical defaulting for
the shared request-budget inputs. The provider-neutral budget contract belongs
to their common workflow surface, even though authentication and transport are
provider-specific.

### Structural regression tests

Tests SHALL assert that every LLM check-step environment applies defaults for
the three request-budget inputs. This protects future workflow steps from
reintroducing the job-versus-step environment mismatch without requiring live
provider access.

## Risks / Trade-offs

- [A new LLM step omits the fallback] → Structural tests enumerate every
  step-level budget mapping in both reusable workflows.
- [An explicitly blank variable is intentionally used to disable a budget] →
  No disable-by-blank behavior is introduced; blank values remain invalid
  overrides when they reach the runtime.

## Migration Plan

Template and instance repositories adopt the updated reusable workflows through
their normal template synchronization or workflow-ref upgrade path. No
configuration migration is needed because organizations that omit optional
variables begin receiving the already documented defaults. Rollback consists of
reverting the workflow change, although that restores the failure for omitted
values in step-level environments.

## Open Questions

None.
