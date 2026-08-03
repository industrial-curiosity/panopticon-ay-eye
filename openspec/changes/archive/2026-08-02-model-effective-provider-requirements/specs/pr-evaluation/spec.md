# PR Evaluation Delta

## ADDED Requirements

### Requirement: Provider workflows resolve effective configuration before preflight

Each provider-specific reusable PR workflow SHALL resolve optional non-secret
provider inputs through the validated contract before provider preflight and
LLM work. It SHALL invoke only the fixed checked-out instance
`.github/actions/panopticon-provider-defaults/action.yml` when an action output
is needed, and SHALL not allow instance configuration or a child caller to
choose another action path. The workflow SHALL preserve raw caller inputs until
resolution so a template workflow default cannot mask a higher-precedence
source. It SHALL expose only source labels in its summary and environment
diagnostics, never a resolved value or credential.

The workflow SHALL receive `job_timeout_minutes` already resolved by the
generated caller. It SHALL NOT attempt to obtain that job-level value from the
fixed instance action because GitHub evaluates job timeout before job steps run.

#### Scenario: Workflow uses a template default only after higher sources are absent

- **GIVEN** an optional input is absent from organization Actions, the fixed
  instance action, and instance configuration but has a declared workflow
  default
- **WHEN** the reusable workflow resolves effective configuration
- **THEN** it uses the workflow default and records `workflow default` as the
  source before provider preflight

#### Scenario: Required input cannot be supplied by a default

- **GIVEN** a required provider input is absent from the child caller
- **WHEN** the reusable workflow starts
- **THEN** it fails before invoking the default-resolver action or provider
  preflight and identifies the required logical name and configuration path

#### Scenario: Job timeout is resolved before the workflow starts

- **GIVEN** an instance configuration supplies a valid non-secret job-timeout
  default and the organization Actions variable is absent
- **WHEN** the generated caller invokes the reusable workflow
- **THEN** the workflow uses the caller-supplied timeout and does not invoke the
  fixed instance action to resolve it

#### Scenario: Fixed default action output is invalid

- **GIVEN** an optional value requires the fixed instance action and the action
  is missing, returns an undeclared output, or returns an empty value
- **WHEN** the reusable workflow resolves effective configuration
- **THEN** it fails before provider preflight and its step summary names the
  fixed path, logical value, and recovery action without printing a value
