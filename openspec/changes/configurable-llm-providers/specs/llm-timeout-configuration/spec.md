# LLM timeout configuration delta

## MODIFIED Requirements

### Requirement: Organization-configurable LLM request budget

The instance provider contract SHALL record configurable org-level Actions variable names for the LLM
request timeout, transport-attempt budget, and correction-attempt budget. Child bootstrap SHALL map the
values of those named variables to canonical provider workflow inputs, and every provider runtime SHALL
apply defaults of 90 seconds, two transport attempts, and two correction retries when a mapped value is
unset. The runtime SHALL reject a blank, non-integer, or out-of-range request timeout (30–300 seconds),
transport attempt count (1–3), or correction retry count (0–2) before sending an LLM request and name both
the configured Actions variable and permitted range in the error.

#### Scenario: No mapped override values configured

- **WHEN** an initialized repository runs an LLM-dependent CI check without values in its configured
  request-budget variables
- **THEN** the selected provider runtime uses a 90-second request timeout, two transport attempts, and two
  correction retries

#### Scenario: Valid request-budget overrides configured

- **WHEN** an organization gives valid values to all three configured request-budget variable names
- **THEN** every LLM-dependent CI check receives and uses those values through canonical provider inputs

#### Scenario: Invalid request-budget override configured

- **WHEN** the configured timeout variable maps the value `five` into a provider workflow
- **THEN** the check fails before sending an LLM request and reports the configured variable name plus the
  integer range 30 through 300

### Requirement: Organization-configurable PR workflow budget

The instance provider contract SHALL record a configurable org-level Actions variable name for the PR job
timeout. Child bootstrap SHALL map its value to a canonical input of the selected provider workflow. Each
provider workflow SHALL default to 20 minutes when the mapped value is unset. The documented valid range
SHALL be 10–60 whole minutes, and GitHub Actions configuration evaluation SHALL reject an invalid value
before the job starts rather than silently coercing it.

#### Scenario: No workflow-budget value configured

- **WHEN** an initialized repository invokes its selected provider workflow without a mapped job-timeout
  value
- **THEN** the evaluate job has a 20-minute timeout

#### Scenario: Valid workflow-budget override configured

- **WHEN** the configured job-timeout variable maps the value `30`
- **THEN** the selected provider workflow's evaluate job has a 30-minute timeout

