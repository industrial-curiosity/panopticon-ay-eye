# contributor-guidance Specification

## Purpose

TBD - created by archiving change add-contribution-guidelines. Update Purpose after archive.

## Requirements

### Requirement: General contribution guidelines are discoverable

The repository SHALL provide a root-level `CONTRIBUTING.md` that explains the
general contribution
workflow, and `README.md` SHALL link to it in the Documentation section.

#### Scenario: A reader starts from the README

- **WHEN** a prospective contributor reads the README documentation links
- **THEN** they can open the general contribution guidelines directly

### Requirement: Contribution guidelines include the OpenSpec workflow

The contribution guidelines SHALL describe OpenSpec as part of the contribution
workflow, including
the roles of current specifications, active changes, and archived changes; the
proposal, design,
specification-delta, and task artifacts; and the commands to list, inspect,
validate, and progress
a change.

#### Scenario: A contributor plans a repository change

- **WHEN** a contributor follows the contribution guidelines before implementing
  a non-trivial change
- **THEN** they can identify the relevant current specification, create or
  inspect a change, and
  validate its artifacts

### Requirement: Contribution guidelines preserve focused references

The contribution guidelines SHALL link to focused repository documentation for
parser contributions
and testing rather than duplicating their detailed instructions.

#### Scenario: A contributor adds a parser

- **WHEN** a contributor uses the general contribution guidelines for parser
  work
- **THEN** the guidelines direct them to the parser contribution guide and test
  documentation

### Requirement: Contribution guidelines identify Markdown validation

The contribution guidelines SHALL identify `markdownlint-cli2` as the
repository's Markdown
validation command and SHALL explain that it runs the installed `markdownlint`
engine.

#### Scenario: A contributor changes Markdown

- **WHEN** a contributor adds or edits a Markdown file
- **THEN** the guidelines direct them to run `markdownlint-cli2 "**/*.md"`
  before completing the
  change

### Requirement: Centered README media has a scoped lint exception

The README SHALL preserve centered media content with an explicitly justified,
MD033-scoped Markdownlint exception around each centered media block.

#### Scenario: A reader views README media

- **WHEN** a reader views the README logo or linked video thumbnail
- **THEN** each media block is centered and the adjacent lint-control comment
  explains why HTML alignment is required
