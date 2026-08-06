# Doc Generation Specification Delta

## ADDED Requirements

### Requirement: Organization-aware index preflight precedes index-derived docs

Documentation generation SHALL complete the organization-aware interface naming
preflight before it renders interface documentation or refreshes an architecture
overview, and it SHALL regenerate the local interface index when that preflight
creates or updates a naming hint. The deterministic interface-doc renderer SHALL
consume the resulting local index only after the preflight succeeds.

#### Scenario: Preflight changes a local name

- **WHEN** documentation generation creates a canonical-name hint for an
  interface after consulting the instance compiled index
- **THEN** it regenerates `panopticon/index.json` before rendering
  `interfaces.md`, and the rendered documentation contains the new canonical
  name
