## 1. Documentation-generation contract

- [x] 1.1 Update the child documentation-generation skill and architecture template so child-local links remain document-relative and the architecture back-link uses `panopticon.org_diagram_link` output verbatim.
- [x] 1.2 Remove the guidance that treats a broken child-repository org-diagram link as expected, while retaining plain Markdown navigation and the instance org diagram's relative child-doc links.

## 2. Regression coverage

- [x] 2.1 Add focused tests that verify the documentation-generation guidance and template require an absolute child-to-org URL and do not reintroduce the location-dependent `../architecture.md#{repo}` back-link.
- [x] 2.2 Preserve and extend diagram-link coverage to demonstrate relative child-local links and the existing absolute resolver behavior in their respective contexts.

## 3. User-facing guidance and validation

- [x] 3.1 Rewrite the setup guide's diagram-navigation section to state that child-local documentation links are relative and org-diagram links are immediately usable absolute GitHub URLs.
- [x] 3.2 Update the testing guide for any added or changed diagram-link regression coverage, then run the relevant test suite and `openspec validate fix-diagram-link-contexts --strict`.
- [x] Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change
