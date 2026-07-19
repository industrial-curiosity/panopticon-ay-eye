# LLM timeout configuration

## ADDED Requirements

### Requirement: Organization-configurable LLM request budget

The CI runtime SHALL read the optional org-level Actions variables `PANOPTICON_LLM_TIMEOUT_SECONDS`, `PANOPTICON_LLM_MAX_ATTEMPTS`, and `PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS`. When a variable is unset, it SHALL use defaults of 90 seconds, two transport attempts, and two correction retries respectively. It SHALL reject a blank, non-integer, or out-of-range configured request timeout (30–300 seconds), transport attempt count (1–3), or correction retry count (0–2) before sending an LLM request, and name the invalid variable and permitted range in the error.

#### Scenario: No override variables configured

- **WHEN** an initialized repository runs an LLM-dependent CI check without any request-budget override variables
- **THEN** the runtime uses a 90-second request timeout, two transport attempts, and two correction retries

#### Scenario: Valid request-budget overrides configured

- **WHEN** an organization configures valid values for all three request-budget variables
- **THEN** every LLM-dependent CI check uses those values for its request timeout and retry budgets

#### Scenario: Invalid request-budget override configured

- **WHEN** an LLM-dependent CI check starts with `PANOPTICON_LLM_TIMEOUT_SECONDS` set to `five`
- **THEN** the check fails before sending an LLM request and reports that the variable must be an integer from 30 through 300

### Requirement: Organization-configurable PR workflow budget

The reusable PR-evaluation workflow SHALL set `jobs.evaluate.timeout-minutes` from the optional org-level Actions variable `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES`, defaulting to 20 minutes when it is unset. The documented valid range SHALL be 10–60 whole minutes. The workflow SHALL not silently coerce an invalid value; GitHub Actions configuration evaluation SHALL reject it before the job starts.

#### Scenario: No workflow-budget override configured

- **WHEN** an initialized repository invokes the reusable PR-evaluation workflow without `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES`
- **THEN** the evaluate job has a 20-minute timeout

#### Scenario: Valid workflow-budget override configured

- **WHEN** an organization configures `PANOPTICON_LLM_JOB_TIMEOUT_MINUTES` to `30`
- **THEN** the evaluate job has a 30-minute timeout
