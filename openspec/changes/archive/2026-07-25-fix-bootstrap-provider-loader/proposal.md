# Fix bootstrap provider loader

## Why

The template-derived instance installer loads `bootstrap.py` without loading
its `providers.py` dependency, so a standard child-repository bootstrap fails
before writing any child files. The public bootstrap path must load the complete
minimal module set required by its default payload.

## What Changes

- Load and register the provider registry before executing the default bootstrap
  payload.
- Cover the production bootstrap import contract in the self-bootstrap tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: Default template-derived instance bootstraps must load
  all required payload modules before invoking bootstrap logic.

## Impact

- `install.py` default-payload loader
- Self-bootstrap regression tests
- Public template and uncustomized instance bootstrap behavior
