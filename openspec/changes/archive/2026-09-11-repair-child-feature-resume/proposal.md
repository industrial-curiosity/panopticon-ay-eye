# Repair Child Feature Resume

## Why

Child initialization can deadlock after feature remediation because its
continuation command requires the instance-only feature registry. This leaves a
stale checkpoint even when the child has the installed feature helper and
receipt needed to repair and validate its own artifacts.

## What Changes

- Make child initialization validate repaired feature artifacts through the
  child receipt and installed helper rather than the instance-only manifest
  command.
- Remove recovery instructions that send child-repo agents to the unavailable
  registry command.
- Cover the no-local-manifest resume path with a regression test.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: enabled feature remediation in a child repo must
  revalidate without requiring the instance feature registry.
- `template-validation-scope`: template pull requests must reject malformed
  workflow YAML before contract validation and tests.

## Impact

- `.agents/skills/panopticon-init/SKILL.md`
- `panopticon/init_repo.py` and its unit tests
- `openspec/specs/repo-initialization/spec.md`
- `.github/workflows/template-validation.yml` and
  `tests/test_workflow_contracts.py`
- `openspec/specs/template-validation-scope/spec.md`
