# Harden bootstrap manifest and workflow CI

## Why

Child bootstrap still chooses vendored tooling from a locally imported Python
manifest rather than from the selected instance ref. The default instance
payload loader also omits that imported module, so an uncustomized instance can
fail before bootstrap begins. Separately, reusable-workflow contract validation
is limited to provider workflows and is not enforced by a repository-owned CI
run.

## What Changes

- Replace the executable local-tooling module manifest with a versioned,
  data-only instance manifest that bootstrap, local sync, and tooling-currency
  validate and consume from the selected instance ref or checkout.
- Make bootstrap stage every manifest-listed module before writing any of them,
  while retaining additive sync behavior and advisory unmanaged-file warnings.
- Remove the default payload loader's dependency on a manifest import so the
  selected instance bootstrap can start without an extra in-memory module.
- Extend deterministic workflow-contract validation to discover every shipped
  reusable workflow instead of keeping a provider-only list.
- Add repository-owned, no-secret CI that runs contract validation and the
  Python test suite for template changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: bootstrap and local sync consume one non-executable,
  versioned manifest from the selected instance.
- `tooling-currency`: advisory tooling comparisons consume the instance
  manifest without relying on a child or executable Python copy.
- `reusable-workflow-contract-validation`: all shipped reusable workflows are
  validated and the validation is enforced in repository CI.

## Impact

- Affects `install.py`, bootstrap and sync tooling, the local-tooling manifest,
  tooling-currency checks, workflow-contract validation, tests, and GitHub
  Actions configuration.
- Adds no runtime LLM provider, credential, or third-party Python dependency.
- Instances must receive the new manifest with the bootstrap and sync code from
  the same selected ref; existing child files remain additive and are never
  deleted automatically.
