# LLM Provider Configuration Delta

## ADDED Requirements

### Requirement: Provider contracts declare effective value sources

The trusted provider registry SHALL declare which selected-provider variable
logical names are optional and which have template workflow defaults. Optional
names SHALL be a subset of the selected provider and credential mode's
registered variables. The instance contract MAY declare non-secret defaults
only for optional names. The instance token, provider credentials, API keys,
and authentication settings SHALL remain required and SHALL NOT be supplied by
an instance default or default-resolver action.

For each optional variable, the effective value SHALL be selected in this order:
an explicit non-empty organization Actions variable, a non-empty output from
the fixed instance default-resolver action, a non-empty non-secret instance
configuration default, then the declared non-empty template workflow default.
If no source supplies a value, provider configuration SHALL fail before
provider preflight or LLM work.

`job_timeout_minutes` SHALL be resolved in the generated caller because GitHub
evaluates job timeout before an instance action can run. Its supported order is
an explicit organization Actions variable, a non-secret instance configuration
default embedded in the generated caller, then the declared template workflow
default. The fixed instance default-resolver action SHALL NOT provide this
value.

#### Scenario: Organization Actions variable has precedence

- **GIVEN** an optional provider variable has values from all four trusted
  sources
- **WHEN** the provider workflow resolves its effective configuration
- **THEN** it uses the organization Actions variable and reports only that
  source label

#### Scenario: Fixed action supplies an absent optional value

- **GIVEN** an optional provider variable is absent from organization Actions
  variables and the fixed instance action returns a non-empty declared output
- **WHEN** the provider workflow resolves its effective configuration
- **THEN** it uses the action output before any instance-configured or workflow
  default

#### Scenario: Caller carries an instance job-timeout default

- **GIVEN** `job_timeout_minutes` is absent from organization Actions variables
  and the instance configuration declares a valid non-secret default
- **WHEN** child bootstrap generates a caller
- **THEN** the caller supplies that default to the reusable workflow before job
  timeout is evaluated and does not invoke the fixed action for it

#### Scenario: Optional value has no effective source

- **GIVEN** an optional provider variable is absent from every permitted source
- **WHEN** the provider workflow resolves its effective configuration
- **THEN** it fails before provider preflight, names the logical value and
  checked sources, and does not display any credential or value

#### Scenario: Invalid optional logical name is rejected

- **WHEN** an instance configuration marks an unregistered or required logical
  name optional or provides it with a default
- **THEN** provider-contract validation fails before writing configuration or
  generating a child caller

### Requirement: Integrator guidance explains effective provider configuration

Provider setup documentation and configuration workflow summaries SHALL present
an organization integrator with a provider-specific table that identifies every
logical value's purpose, required or optional status, allowed source(s) in
precedence order, configured Actions name when applicable, and a concrete next
action. The guide SHALL give an ordered setup path for the organization-variable
only case and a separate, clearly labelled path for the fixed instance default
resolver. It SHALL state that neither path accepts, stores, or displays
credential values.

#### Scenario: Integrator configures a provider with only organization values

- **WHEN** an integrator follows the provider setup guide without an instance
  default or default-resolver action
- **THEN** the guide identifies the required Actions names, verification
  command, expected result, and child-bootstrap command without requiring
  knowledge of implementation source

#### Scenario: Integrator needs dynamic optional defaults

- **WHEN** an integrator chooses the fixed instance default-resolver action
- **THEN** the guide names its fixed path, declared outputs, precedence, safe
  validation command, and recovery for a missing or invalid output without
  exposing credential values

## MODIFIED Requirements

### Requirement: Provider configuration has a deterministic revision

The effective provider contract SHALL have a deterministic revision derived from
all caller-relevant configured names, provider identity, credential mode,
permissions, workflow path, optionality declarations, instance defaults,
template defaults, and fixed default-resolver-action contract. Generated child
callers SHALL record and reusable workflows SHALL compare this revision before
provider-dependent work so an old caller cannot silently use a changed provider
configuration.

#### Scenario: Provider configuration changes after child bootstrap

- **WHEN** an instance changes a configured provider name, credential mode,
  optionality declaration, default source, or default-resolver-action contract
- **THEN** an existing child invokes a caller with its previous revision
- **THEN** the reusable workflow fails before provider work and prints the
  child-bootstrap recovery command

#### Scenario: Provider configuration is unchanged

- **WHEN** the generated caller revision matches the effective live instance
  contract
- **THEN** the reusable workflow proceeds with provider preflight
