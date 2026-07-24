# Architecture Diagrams Delta

## ADDED Requirements

### Requirement: Org diagram is template-declared and instance-owned during sync

The template SHALL declare `docs/architecture.md` as an instance-owned generated
path for template-sync
merges. The template's tracked copy is an installable empty-state placeholder,
not the durable source of
truth after an instance has generated or otherwise acquired its own copy. When
the path exists on both
sides of a template merge, the instance's current copy SHALL win. When it exists
only in the incoming
template, the placeholder SHALL be installed.

This classification SHALL be fixed by the template and SHALL NOT be modeled as
protected JSON configuration,
an entry in `PROTECTED_CONFIG_FILES`, an org-declared `protected_paths`
customization, or a tracked
`.gitattributes` rule. It SHALL use the template-sync workflow's per-checkout
`.git/info/attributes`
registration and existing `merge.ours.driver true` configuration.

#### Scenario: Generated instance diagram is preserved

- **GIVEN** both the instance and incoming template contain
  `docs/architecture.md`
- **WHEN** template sync merges the histories and Git requires a path-level
  merge decision
- **THEN** the instance's current generated content is retained

#### Scenario: Placeholder bootstraps a missing diagram

- **GIVEN** the incoming template contains the empty-state placeholder and the
  instance has no
  `docs/architecture.md`
- **WHEN** template sync merges the histories
- **THEN** the placeholder is added to the instance and its README architecture
  link resolves

#### Scenario: Generated path is not reported as customization

- **WHEN** template sync registers `docs/architecture.md` in
  `.git/info/attributes`
- **THEN** the workflow identifies it as a template-declared generated path and
  does not describe it as
  protected configuration or org customization
