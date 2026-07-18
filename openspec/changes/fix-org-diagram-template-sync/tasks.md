# Org Diagram Template Sync Fix Tasks

## 1. Workflow Registration

- [ ] 1.1 Update `sync-from-template.yml` to declare `docs/architecture.md` as a fixed instance-owned generated path and write it to `.git/info/attributes` before merging
- [ ] 1.2 Reuse the existing `merge.ours.driver true` registration while keeping generated paths separate from `PROTECTED_CONFIG_FILES` and org-declared `protected_paths`
- [ ] 1.3 Update workflow comments and the step summary so the generated path is labeled separately from org customization

## 2. Git Integration Coverage

- [ ] 2.1 Refactor the real-git test helper to reproduce both fixed generated-path and dynamic customization registration without conflating their classifications
- [ ] 2.2 Add routine-sync coverage where the template and instance independently add `docs/architecture.md`
- [ ] 2.3 Add routine-sync coverage where both sides modify an existing `docs/architecture.md`
- [ ] 2.4 Add first-sync coverage where unrelated histories contain different versions of `docs/architecture.md`
- [ ] 2.5 Add coverage proving the template placeholder is installed when the instance does not have `docs/architecture.md`
- [ ] 2.6 Run the focused sync integration tests, the complete test suite, and strict OpenSpec validation

## 3. Documentation

- [ ] 3.1 Update sync and testing documentation to explain the template-declared, instance-owned generated path and the one-time rollout requirement for existing instances
- [ ] Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
