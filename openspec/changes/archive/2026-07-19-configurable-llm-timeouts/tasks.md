# Configurable LLM timeouts tasks

## 1. Runtime configuration

- [x] 1.1 Add named defaults, bounds, and strict environment parsing for the
  three LLM request-budget variables in `panopticon/llm.py`.
- [x] 1.2 Make `LLMClient.from_env` pass the validated timeout and retry values
  into the shared client and preserve explicit constructor overrides used by
  tests.
- [x] 1.3 Extend `tests/test_llm.py` for defaults, valid overrides, all
  invalid-value classes, transport retry limits, correction retry limits, and
  no-request-on-validation-failure behavior.

## 2. Workflow configuration

- [x] 2.1 Set `jobs.evaluate.timeout-minutes` from
  `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES` with a 20-minute `fromJSON` fallback in
  `.github/workflows/panopticon-pr.yml`.
- [x] 2.2 Pass the three request-budget variables to every LLM-dependent
  workflow step and update workflow tests or validation coverage for the default
  and override expression.

## 3. Specifications and documentation

- [x] 3.1 Update the canonical agent-runtime and PR-evaluation specifications
  with the accepted timeout configuration requirements.
- [x] 3.2 Update `docs/setup-guide.md` with the four variables, defaults,
  ranges, override scope, and the LiteLLM-proxy timeout relationship.
- [x] 3.3 Update README.md and docs/testing.md to reflect the user-facing
  configuration and its coverage; `docs/architecture.md` is generated from
  organization indices and does not describe this runtime setting.

## 4. Verification

- [x] 4.1 Run the focused LLM runtime and workflow validation tests, then run
  the repository test suite required by the changed modules.
- [x] 4.2 Validate the OpenSpec change strictly and confirm the documented
  default worst-case budget remains within the 20-minute job limit.
