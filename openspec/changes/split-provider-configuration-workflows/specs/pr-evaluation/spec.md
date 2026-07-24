# PR evaluation delta

## MODIFIED Requirements

### Requirement: Legacy and stale callers fail with complete recovery instructions

The instance SHALL retain a legacy `panopticon-pr.yml` guard for callers generated before provider
selection and each provider workflow SHALL validate its configuration revision and canonical required
values before provider-dependent work. A legacy, stale, or empty renamed-secret path SHALL fail as an
operational error with a concise annotation and a detailed step summary. When configuration is required,
the summary SHALL state the cause, show the resolved instance's direct LiteLLM and Bedrock configuration
workflow URLs, give ordered provider-choice console instructions and equivalent `gh workflow run` commands
for both provider entrypoints, and give the exact one-line child bootstrap command plus commit, push, and
rerun instructions when caller regeneration is required.

#### Scenario: Legacy generic caller runs against an unconfigured instance

- **WHEN** a child still references instance workflow `panopticon-pr.yml` and the resolved instance has no
  selected provider
- **THEN** the guard fails after reading the child instance identity and prints both provider-specific
  configuration paths plus complete child-bootstrap recovery commands rather than producing a workflow-load
  error

#### Scenario: Provider revision is stale

- **WHEN** a provider workflow receives a configuration revision different from the live instance contract
- **THEN** it fails before LLM checks and prints an exact installer command in the form
  `curl -fsSL <public-installer-url> | PANOPTICON_INSTANCE='<owner/repo>' python3`
