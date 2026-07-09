# Testing

Panopticon's Python tooling is stdlib-only (see `.agents/skills/panopticon-python-tooling`), and so is its
test suite: plain `unittest`, no third-party test runner, no build step.

## Running the suite

```bash
python3 -m unittest discover -t . -s tests
```

- **Prerequisites:** a repo checkout and a system `python3` (3.9+). Nothing to install.
- **Pass criteria:** exit code 0 with `OK` in the summary line. Any `FAILED` or `ERROR` output is a failure.
- **Ordering:** tests are independent; discovery order does not matter.

Run a single module while iterating:

```bash
python3 -m unittest tests.test_merge -v
```

## Suite layout

| Module | Covers |
| --- | --- |
| `tests/test_config.py` | Org gating config defaults and overrides, workflow ref policy, child repo config round-trips |
| `tests/test_currency.py` | Index-currency verdict parsing, loud failures on malformed verdicts, report formatting |
| `tests/test_docs.py` | Deterministic interface-doc rendering, in-place regeneration and component pruning, four-layer validation |
| `tests/test_drift.py` | Doc-drift verdict parsing, loud failures on malformed verdicts, PR-comment report formatting |
| `tests/test_extraction.py` | Parser-candidate folding into a local index, LLM fallback tagging (`extracted_by: llm`), parser-gap recommendations, CI changed-file scoping |
| `tests/test_index.py` | Index schema validation, deterministic save/load round-trips |
| `tests/test_init_repo.py` | Init validation gate (config written only when docs/index pass), caller-workflow wiring, docs-location adoption, idempotent re-init, report-only secret verification (gh CLI stubbed; no network) — including manual verification steps printed when `gh` is missing or unauthenticated |
| `tests/test_install.py` | Bootstrap installer (`install.py`): skill download filtering, caller-workflow wiring, `PANOPTICON_INSTANCE` env/prompt resolution, token resolution (`GH_TOKEN`/`GITHUB_TOKEN`/`gh auth token`), org CI prerequisite reporting including the token-less manual-verification-steps path, `main()`'s `workflow_ref` default (falls back to the instance repo's default branch, not a tag, when org config omits it), IDE/tool compatibility selection and reconciliation (`PANOPTICON_IDES`/`PANOPTICON_IDE_RECONCILE` env overrides, duplicate/symlink/single-IDE strategies, idempotent re-run detection, symlink-failure reporting), agent prompt text (all network calls stubbed) |
| `tests/test_merge.py` | Shard replace, compiled-index rebuild reproducibility, conflict detection, simulation/merge parity, the `python3 -m panopticon.merge` CLI used by CI (exit code 2 = new conflicts) |
| `tests/test_llm.py` | CI agent runtime: request shape, retries, fail-loudly degradation paths, skill loading (uses an in-process stub `/chat/completions` server; no network) |
| `tests/test_naming.py` | Name normalization rules, `panopticon-` hint parsing, CI name-resolution failures |
| `tests/test_parsers.py` | Parser registry detection plus the REST/OpenAPI and Kafka starter parsers |

Fixtures live in `tests/fixtures/`: sample local index documents (`local_*.json`) and a `sample_repo/` tree
exercised by the parser tests. Tests that need to write files use `tempfile` and clean up after themselves —
never add fixtures that tests mutate in place.
