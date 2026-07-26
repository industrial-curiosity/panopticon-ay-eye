# Architecture link protocol design

## Context

Child documentation is visible in two locations: the child repository and the
instance repository's `docs/{repo}/` mirror. A child README was corrected to
use the resolver-produced absolute org-diagram URL, but the architecture
overview can still use a relative org-diagram back-link.

## Goals / Non-Goals

**Goals:**

- Apply one complete navigation-link protocol across generated child README and
  architecture-overview content.
- Preserve relative links only where both document locations share the same
  relative relationship.
- Detect regressions across generation guidance and the architecture template.

**Non-Goals:**

- Change the org-diagram link resolver, branch-resolution behavior, or GitHub
  rendering behavior.
- Add a new CI-only checker for arbitrary user-authored links.

## Decisions

### Treat the resolver output as the single source of truth for child-to-org links

Both generated child README org links and architecture-overview back-links use
`python3 -m panopticon.org_diagram_link` verbatim. This avoids two separate
implementations of the instance URL and branch fallback logic.

### Make the protocol location-aware

Child-local links remain relative to the document that contains them. Links
from a child document to the organization diagram are absolute because the
child repository and instance mirror do not share a stable relative path.
Links from the instance org diagram to a mirrored child architecture document
remain `{repo}/architecture.md`, relative to `docs/architecture.md`.

### Test the generated surfaces together

Regression tests inspect the generation skill and architecture template as a
set, so a README-only fix cannot leave the child architecture overview with an
old relative org link.

## Risks / Trade-offs

- Agent-authored existing documentation may retain an old link until refreshed
  → generation guidance explicitly replaces it during a normal update.
- A template-only assertion can miss wording drift in guidance → tests cover
  both the template and the skill.

## Migration Plan

Ship the guidance, template, and tests together. Regenerate or refresh child
documentation to replace legacy relative org-diagram back-links; no data or
configuration migration is required.

## Open Questions

None.
