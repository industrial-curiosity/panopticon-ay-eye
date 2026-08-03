# Restrict Child Sync Tooling Manifest

## Why

Child resource sync currently copies every file under `panopticon/`, including
CI-only runtime modules and provider dependencies that are not supported in
child-local execution. This breaks the intended local/CI module boundary and
expands every child repository's managed surface unnecessarily.

## What Changes

- Define an instance-owned child-safe tooling manifest.
- Make child sync download the manifest on every run, then preview and update
  only its listed modules.
- Keep CI-only modules such as the LLM runtime out of child updates.
- Add regression coverage for manifest parity, filtering, and existing child
  files outside the manifest.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: Bootstrap and resource sync must manage the same
  explicit subset of child-local tooling.

## Impact

This change affects the local-tooling manifest, bootstrap, sync, sync tests,
and child-sync documentation. No credentials, provider configuration, or CI
runtime behavior changes.
