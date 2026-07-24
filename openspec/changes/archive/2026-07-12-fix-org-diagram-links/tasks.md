# 2026 07 12 Fix Org Diagram Links Tasks

## 1. Fix link generation

- [x] 1.1 In `panopticon/diagrams.py`'s `render_org_diagram()`, change the
  per-repo section's
      own-diagram link from
      `[docs/{repo}/architecture.md](docs/{repo}/architecture.md)` to
      `[{repo}/architecture.md]({repo}/architecture.md)`
- [x] 1.2 In `panopticon/diagrams.py`'s `_table()`, change the "Other repo"
  column link from
      `[{other}](docs/{other}/architecture.md)` to
      `[{other}]({other}/architecture.md)`

## 2. Strengthen tests

- [x] 2.1 Update
  `tests/test_diagrams.py::test_navigation_links_to_child_repo_docs` to assert
  the
      literal correct hrefs (`svc-a/architecture.md`, `svc-b/architecture.md`)
      are present and the
      buggy form (`docs/svc-a/architecture.md`, `docs/svc-b/architecture.md`) is
      absent
- [x] 2.2 Run `python3 -m pytest tests/test_diagrams.py -v` and confirm all
  tests pass

## 3. Update spec

- [x] 3.1 Confirm
  `openspec/changes/fix-org-diagram-links/specs/architecture-diagrams/spec.md`'s
      MODIFIED requirement accurately reflects the implemented href form
      (already drafted; verify
      against the final code)

## 4. Docs

- [x] 4.1 Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes
      introduced by this change (README.md's diagram descriptions describe the
      file's location/
      behavior, not the link href literal — no change needed there; no
      docs/spec.md exists in this
      repo; updated docs/testing.md's `test_diagrams.py` summary to match the
      corrected href;
      hygienist sweep found no other stale references)
