# Add contribution guidelines

## Why

The README directs prospective contributors only to the parser guide, leaving
the general
contribution process and the repository's OpenSpec workflow undiscoverable. A
single,
visible guide will make the expected path to propose, implement, validate, and
document
changes clear.

## What Changes

- Add root-level contribution guidelines covering the repository's contribution
  workflow.
- Make OpenSpec artifacts, commands, validation, and lifecycle part of those
  guidelines.
- Link the contribution guidelines prominently from the README while retaining
  the
  parser-specific guide as focused reference material.

## Capabilities

### New Capabilities

- `contributor-guidance`: Discoverable, repository-specific guidance for
  contributing through
  OpenSpec and for following focused contribution references.

### Modified Capabilities

None.

## Impact

This affects `README.md`, a new root-level `CONTRIBUTING.md`, and repository
documentation.
It introduces no runtime, API, dependency, or generated-child-repository
behavior changes.
