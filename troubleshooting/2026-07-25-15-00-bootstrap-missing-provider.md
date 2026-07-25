# Bootstrap missing provider module

**Date**: 2026-07-25
**Context**: The public launcher fetched an instance installer that failed with
`ModuleNotFoundError: No module named 'panopticon.providers'`.

---

## Attempt 1 — Trace the self-bootstrap import path

**Hypothesis**: The default instance payload loads `bootstrap.py` without
loading all of its package-relative imports.
**What was tried**: Read `install.py`'s `_load_default_payload_from_github`,
`panopticon/bootstrap.py`, and the self-bootstrap test.
**Result**: The loader fetches and registers only `__init__.py`, `recovery.py`,
and `bootstrap.py`. `bootstrap.py` imports `panopticon.providers`, which is not
registered or fetched.
**Status**: ⚠️ Partial — the local control flow matches the reported failure;
the deployed source still needs confirmation.

---

## Attempt 2 — Check regression coverage

**Hypothesis**: The self-bootstrap test uses a simplified bootstrap payload
that omits the provider import, so it cannot detect this failure.
**What was tried**: Read `TestDefaultInstancePayload` in
`tests/test_install_self_bootstrap.py`.
**Result**: Its fake bootstrap imports only `SCHEMA_VERSION` and `recovery`,
then expects three fetched modules. It does not exercise the production
`providers` import.
**Status**: ✅ Resolved

---

## Attempt 3 — Confirm the deployed instance source

**Hypothesis**: The public `main` revision fetched by the failing command has
the same incomplete loader as the local source.
**What was tried**: Read the public instance's `install.py` and
`panopticon/bootstrap.py` at `main`, and checked the provider module URL.
**Result**: The deployed loader registers only `__init__`, `recovery`, and
`bootstrap`; deployed `bootstrap.py` imports `.providers`; and deployed
`panopticon/providers.py` exists.
**Status**: ✅ Resolved

---
