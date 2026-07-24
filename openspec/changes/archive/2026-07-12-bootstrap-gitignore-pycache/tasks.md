# 2026 07 12 Bootstrap Gitignore Pycache Tasks

## 1. Implement

- [x] 1.1 In `panopticon/bootstrap.py`, add a
  `write_local_tooling_gitignore(child_root=".")`
      function that writes `panopticon/.gitignore` containing `__pycache__/\n`,
      creating the
      `panopticon/` directory if absent
- [x] 1.2 Call it from `main()` right after `download_local_tooling()` succeeds,
  printing a
      one-line confirmation consistent with the surrounding step's output style

## 2. Test

- [x] 2.1 In `tests/test_install.py`, added a sibling
  `TestWriteLocalToolingGitignore` class
      covering: the file is created with the right content on a fresh bootstrap;
      re-running
      overwrites it without duplicating content; `panopticon/` is created if it
      doesn't already
      exist. Also fixed
      `TestMainSkillsLocationFlow::test_local_tooling_vendored_alongside_skills`,
      an existing test whose exact-file-set assertion on `panopticon/` broke
      once `main()` started
      writing `.gitignore` there
- [x] 2.2 Run `python3 -m pytest tests/test_install.py -v` and confirm all tests
  pass (93/93 passed)

## 3. Docs

- [x] 3.1 Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes
      introduced by this change (README.md's `panopticon/` description covers
      the template repo's
      own layout, unrelated to a bootstrapped child repo's vendored subset — no
      change needed; no
      docs/spec.md exists in this repo; updated docs/testing.md's
      `test_install.py` summary via
      hygienist sweep)
