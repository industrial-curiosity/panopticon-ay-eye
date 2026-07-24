# Contribution guidelines design

## Context

The template repository has a parser-specific contribution guide, but no general
entry point for
contributors. Its README does not explain that OpenSpec is the process used to
propose, plan,
validate, and archive repository changes. The new guidance must be useful to
contributors without
turning the README into a procedural manual.

## Goals / Non-Goals

## Goals

- Make a general contribution guide visible from the README.
- Establish OpenSpec as part of the normal contribution workflow.
- Explain which OpenSpec artifacts are authoritative, active, and historical.
- Direct specialized work to its focused existing documentation.

## Non-Goals

- Change the OpenSpec schema, CLI, agent skills, or repository contribution
  policy.
- Duplicate parser implementation details or test instructions that existing
  focused documents own.
- Add generated-child-repository documentation requirements.

## Decisions

### D1: Use a root-level CONTRIBUTING.md as the single contributor entry point

GitHub and common repository conventions make `CONTRIBUTING.md` the expected
location for general
guidance. The README will link to it prominently, while the guide will link
onward to focused
documentation such as the parser guide and testing guide.

Alternative considered: a separate `docs/openspec.md`. This would separate
OpenSpec from the
contribution process and add another starting point, so it is not selected.

### D2: Describe OpenSpec by artifact role and lifecycle

The guidelines will distinguish current requirements in `openspec/specs/`,
active changes in
`openspec/changes/`, and completed history in `openspec/changes/archive/`. It
will name the
proposal, design, specification delta, and task artifacts, and show the
repository's normal
explore, propose, apply, validate, and archive lifecycle.

Alternative considered: listing only CLI commands. Commands without their
artifact purpose make it
hard for contributors to know what to read or update.

### D3: Keep README navigation concise

The README will add a clearly labeled contribution-guidelines link in its
Documentation section.
It will retain the existing parser-guide link instead of restating detailed
workflows in the
README.

### D4: Scope centered-media lint exceptions to README blocks

The README will retain HTML only for centered media blocks. Each block will use
an adjacent, explicitly justified MD033 Markdownlint control instead of a
repository-wide HTML allowance. Markdown does not provide equivalent alignment,
while a global exception would permit unrelated HTML.

## Risks / Trade-offs

- Documentation can drift from the OpenSpec CLI or artifact layout → Use stable
  repository paths
  and only the workflow commands contributors need.
- The guide can duplicate specialized documentation → Link to existing parser
  and test guidance
  rather than reproducing their detailed contracts.
- A long contribution guide can hide the starting workflow → Lead with the
  OpenSpec lifecycle and
  use short, purpose-based sections.
- A local lint exception can spread to unrelated content → Scope each MD033
  control to one README media block and document why it is needed.

## Migration Plan

1. Add `CONTRIBUTING.md` and the README link.
2. Validate the OpenSpec artifacts and Markdown formatting with the repository's
   normal checks.

No migration, rollout, or rollback procedure is required because this change
adds documentation
only.

## Open Questions

None.
