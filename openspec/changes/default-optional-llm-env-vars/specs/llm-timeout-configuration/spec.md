# LLM timeout configuration delta

## MODIFIED Requirements

### Requirement: Organization-configurable LLM request budget

The instance provider contract SHALL record configurable org-level Actions
variable names for the LLM request timeout, transport-attempt budget, and
correction-attempt budget. Child bootstrap SHALL map the values of those named
variables to canonical provider workflow inputs. Every provider runtime and
every LLM-invoking step environment SHALL apply defaults of 90 seconds, two
transport attempts, and two correction retries when a mapped value is absent.
The runtime SHALL reject a blank, non-integer, or out-of-range request timeout
(30–300 seconds), transport attempt count (1–3), or correction retry count
(0–2) before sending an LLM request and name both the configured Actions
variable and permitted range in the error.

#### Scenario: No mapped override values configured

- **WHEN** an initialized repository runs an LLM-dependent CI check without
  values in its configured request-budget variables
- **THEN** the selected provider runtime uses a 90-second request timeout, two
  transport attempts, and two correction retries

#### Scenario: Optional variables are absent at a check step

- **WHEN** an LLM-invoking step in either provider workflow receives no input
  value for the configured request timeout, transport-attempt, or
  correction-attempt variable
- **THEN** that step supplies 90 seconds, two transport attempts, and two
  correction retries to the LLM runtime

#### Scenario: Valid request-budget overrides configured

- **WHEN** an organization gives valid values to all three configured
  request-budget variable names
- **THEN** every LLM-dependent CI check receives and uses those values through
  canonical provider inputs

#### Scenario: Invalid request-budget override configured

- **WHEN** the configured timeout variable maps the value `five` into a
  provider workflow
- **THEN** the check fails before sending an LLM request and reports the
  configured variable name plus the integer range 30 through 300
