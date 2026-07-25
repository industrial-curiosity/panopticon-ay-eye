# Contributing to Panopticon

Panopticon changes are planned and tracked with OpenSpec. Use this guide for
code, workflow,
documentation, parser, and skill contributions.

## Start with the current contract

Before changing behavior, find the relevant requirement under
[`openspec/specs/`](openspec/specs/). These specifications describe the accepted
behavior of the
repository. Use `openspec list --specs` to browse them and `openspec show &lt;name&gt;
--type spec` to
inspect one.

For a non-trivial change, create or join an OpenSpec change before
implementation. Use
`openspec list --json` to see active changes.

## Work through an OpenSpec change

OpenSpec records a change in `openspec/changes/<change-name>/`:

- `proposal.md` explains why the change is needed and its scope.
- `design.md` records implementation decisions and trade-offs.
- `specs/<capability>/spec.md` adds or changes requirements.
- `tasks.md` is the implementation checklist; update its checkboxes as work
  completes.

When a change is complete, archive it under `openspec/changes/archive/`.
Archived changes preserve
the decision history; the corresponding accepted requirements live in
`openspec/specs/`.
[`openspec/config.yaml`](openspec/config.yaml) supplies the project context and
settled constraints
that apply when creating artifacts.

The normal lifecycle is:

1. Explore the problem with `/openspec-explore` when requirements or trade-offs
   need investigation.
2. Create a complete change with `/openspec-propose`, or begin manually with
   `openspec new change "<change-name>"`.
3. Use `/openspec-update-change` to add, modify, or remove requirements and
   scenarios. It updates a related active change's delta specification, or the
   canonical specification when appropriate.
4. Read the proposal, design, requirement deltas, and tasks; then implement with
   `/openspec-apply-change`.
5. Check progress with `openspec status --change "<change-name>"` and validate
   with
   `openspec validate --strict "<change-name>"`.
6. Archive finished work with `/openspec-archive-change` or `openspec archive
   "<change-name>"`.

Use the OpenSpec agent skills in [`.agents/skills/`](.agents/skills/) when
working with an agent:
`/openspec-explore`, `/openspec-propose`, `/openspec-update-change`,
`/openspec-apply-change`, and `/openspec-archive-change`. They read and
maintain the applicable artifacts in the correct order.

## Make and validate the change

Keep changes focused, update any requirements that behavior changes, and
complete the corresponding
tasks. Run the validation named by the change's tasks, including strict OpenSpec
validation. The
[testing guide](docs/testing.md) documents the test suite and its standard
command.

For Markdown changes, run `markdownlint-cli2 "**/*.md"`. This command uses the
installed
`markdownlint` engine to check Markdown formatting before the change is
complete.

## Follow focused guides

- For deterministic interface or dependency parsers, follow the
  [parser contribution guide](docs/parser-contribution.md).
- For tests and fixtures, follow the [testing guide](docs/testing.md).
- For project setup and instance operations, follow the [org-owner setup
  guide](docs/setup-guide.md).
