## 1. Link protocol enforcement

- [x] 1.1 Update `panopticon-doc-generation` guidance so architecture-overview
  refreshes replace legacy relative org-diagram back-links with the
  resolver-produced absolute URL.
- [x] 1.2 Update the architecture overview template so its org-diagram link and
  all child-local links follow the location-aware protocol.
- [x] 1.3 Verify the deterministic org-diagram renderer retains
  `{repo}/architecture.md` for org-to-child navigation.

## 2. Regression coverage

- [x] 2.1 Extend architecture-link tests to assert the README, child
  architecture template, and generation guidance all require the absolute
  resolver-produced org link.
- [x] 2.2 Add coverage that child-local links remain document-relative and
  org-to-child links remain `{repo}/architecture.md`.

## 3. Documentation and verification

- [x] 3.1 Update `docs/testing.md`, run the relevant test suite, and run
  `openspec validate enforce-architecture-link-protocol --strict`.
- [x] Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
