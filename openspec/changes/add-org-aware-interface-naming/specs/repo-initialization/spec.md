# Repo Initialization Specification Delta

## ADDED Requirements

### Requirement: Child configuration records an optional conflict-gating override

Child repository `panopticon/config.json` files SHALL accept an optional
`gating.interface-conflict` field whose value is `advisory` or `blocking`.
Initialization and re-initialization SHALL preserve a valid existing override.
An invalid child override SHALL fail clearly before PR gating is evaluated and
identify the child configuration path and accepted values.

#### Scenario: Existing child override survives re-initialization

- **WHEN** an initialized child repository has
  `gating.interface-conflict: blocking` and initialization is re-run
- **THEN** its configuration retains the override unchanged

#### Scenario: Invalid child override fails clearly

- **WHEN** a child configuration sets `gating.interface-conflict` to an
  unsupported value
- **THEN** initialization or PR evaluation reports the child configuration path
  and states that only `advisory` and `blocking` are accepted
