# Bootstrap provider loader design

## Context

The public launcher executes an instance's `install.py`. When that installer is
the uncustomized template payload, it dynamically fetches and registers a small
set of `panopticon` modules before invoking `bootstrap.main`. The production
bootstrap module imports the provider registry, but the loader currently omits
that dependency.

## Goals / Non-Goals

**Goals:**

- Load every direct module dependency needed to import the default bootstrap.
- Preserve the existing isolated in-memory package loading model.
- Prove the real provider dependency is available before bootstrap execution.

**Non-Goals:**

- Change provider configuration semantics or add a package installer.
- Vendor additional tooling into child repositories as part of loader repair.
- Change customized instance installer execution.

## Decisions

Load `panopticon.providers` through the same authenticated contents API and
register it under the in-memory package before loading `bootstrap.py`. This
keeps the payload self-contained and uses the already-established module loader
path rather than changing `sys.path` or writing temporary files.

The regression test will use a bootstrap payload that imports the provider
module and assert the additional file request. A synthetic dependency is not
sufficient because it could drift from the production import contract.

## Risks / Trade-offs

- A future bootstrap import can create another missing dynamic dependency →
  keep the self-bootstrap test aligned with production imports.
- Loading the provider registry adds one contents request → it is required for
  successful bootstrap and remains authenticated through the existing path.
