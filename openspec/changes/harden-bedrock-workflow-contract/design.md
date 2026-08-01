# Bedrock Workflow Contract Design

## Context

The Bedrock PR-evaluation workflow contains references to LiteLLM-only
`inputs.endpoint` and `secrets.api_key` values that its `workflow_call`
contract does not declare. GitHub validates reusable-workflow calls before it
creates a job, so affected callers fail with a zero-job startup error.

Panopticon is a checkout-and-run, standard-library-first template. The
validation must therefore work on workflow source text without adding a YAML
library or relying on GitHub-hosted validation tooling.

## Goals / Non-Goals

**Goals:**

- Remove the invalid Bedrock references.
- Detect undeclared `inputs.<name>` and `secrets.<name>` references in each
  provider PR workflow deterministically during repository tests.
- Keep the checker small, importable, and independent of provider SDKs.
- Make the zero-job failure and recovery path discoverable to maintainers.

**Non-Goals:**

- Fully parse YAML or validate arbitrary GitHub Actions syntax.
- Validate caller workflows, expression contexts other than `inputs` and
  `secrets`, or non-provider workflows in this change.
- Change provider credentials, request bodies, gating, or Bedrock runtime
  behavior.

## Decisions

### Use a constrained source scanner

The checker SHALL inspect only the current, stable reusable-workflow shape:
the `on.workflow_call.inputs` and `on.workflow_call.secrets` mappings, plus
dot-form GitHub expressions that reference `inputs` or `secrets`. It will use
indentation to identify direct mapping keys and a regular expression to collect
the dot-form references.

This is sufficient for the shipped provider workflows and preserves the
standard-library, checkout-and-run constraint. A general YAML parser was
rejected because it adds a dependency and can interpret GitHub Actions YAML
differently from GitHub, especially around `on`.

### Report contract errors as data

The importable validator SHALL return a stable, sorted collection of undeclared
references. A thin command-line entry point may turn those errors into a
non-zero result for automation, while unit tests assert the exact error list.
Returning data keeps the validation reusable without coupling it to a test
framework or workflow runtime.

### Validate every shipped provider PR workflow

Tests SHALL enumerate the LiteLLM, OpenAI, and Bedrock reusable PR workflows
and validate each. A focused invalid fixture SHALL demonstrate that an
undeclared secret or input is rejected; Bedrock-specific assertions SHALL prove
it no longer references LiteLLM endpoint or API-key configuration.

## Risks / Trade-offs

- [A future workflow uses YAML syntax outside the constrained scanner's scope]
  → Keep the scanner's supported shape explicit, add a fixture before adopting
  new syntax, and use GitHub's own validation as the final deployment check.
- [A string or comment resembles a GitHub expression] → Scan only expression
  delimiters and report a stable, reviewable error that is covered by tests.
- [The validation is bypassed outside the normal test suite] → Expose a thin
  command-line entry point and document the test/validation command for
  maintainers.

## Migration Plan

1. Repair the Bedrock workflow and add the validator with regression tests.
2. Run the full standard-library test suite and strict OpenSpec validation.
3. Release the corrected template; instance repositories receive it through
   their established template-sync process.
4. If an unexpected scanner false positive occurs, revert the template release
   or adjust the scanner and fixture before retrying sync. The change does not
   migrate stored configuration or credentials.

## Open Questions

None.
