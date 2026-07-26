# Architecture diagram link protocol delta

## ADDED Requirements

### Requirement: Complete generated child architecture link protocol

The system SHALL apply the same link protocol to every generated child
architecture navigation surface through the `panopticon-doc-generation` skill
and its architecture overview template. The generated link surfaces include
the child README and child architecture overview. Links from either surface to
the organization diagram SHALL use exactly the absolute URL printed by
`python3 -m panopticon.org_diagram_link`. Links between documents in the child
documentation tree SHALL remain relative to the document that contains them.
The instance org diagram's links to mirrored child architecture documents SHALL
remain `{repo}/architecture.md`, relative to `docs/architecture.md`.

When the skill refreshes a child architecture overview, it SHALL replace a
legacy relative org-diagram back-link with the resolver-produced absolute URL.

#### Scenario: Child architecture overview uses the org-link resolver

- **GIVEN** a child repo with `repo: "svc-a"`,
  `instance: "acme/panopticon-instance"`, and
  `instance_default_branch: "main"`
- **WHEN** doc generation creates or refreshes its architecture overview
- **THEN** the `## Architecture diagram` section contains
  `[org diagram](https://github.com/acme/panopticon-instance/blob/main/docs/architecture.md#svc-a)`
  from `python3 -m panopticon.org_diagram_link`, not a relative org-diagram
  link

#### Scenario: All generated architecture navigation surfaces use their protocol

- **WHEN** the child README, child architecture overview, and instance org
  diagram are generated or refreshed
- **THEN** child-to-org links are resolver-produced absolute URLs, child-local
  links are document-relative, and org-to-child links use
  `{repo}/architecture.md`
