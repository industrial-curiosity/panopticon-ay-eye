# 2026 07 12 Robust Llm Verdicts Tasks

## 1. Shared `complete_json` on `LLMClient`

- [x] 1.1 Add a private `_strip_code_fence(text)` helper to `panopticon/llm.py`
  (move the identical
      logic currently duplicated in `drift.py`, `currency.py`, and
      `extraction.py` — don't leave
      those copies in place once call sites migrate in section 2)
- [x] 1.2 Add `LLMClient.complete_json(skill_text, user_content, validate, *,
  response_label,
      expected_shape, temperature=0, max_correction_attempts=2)`: sends the
      skill-based chat
      request, strips code fences, `json.loads`s the response, calls
      `validate(parsed)` (raises
      `ValueError` on a shape problem); on any `(json.JSONDecodeError,
      ValueError)`, appends the
      failed response as an `assistant` turn plus a corrective `user` turn
      naming the specific
      error and restating "respond with ONLY the JSON `{expected_shape}` — no
      prose, no code
      fences, no explanation", then retries (same conversation, growing) up to
      `max_correction_attempts` additional times; raises `LLMResponseError` with
      `response_label`
      and the last error/response once the budget is exhausted
- [x] 1.3 Unit tests in `tests/test_llm.py`: first-attempt success (no retry
  triggered); a
      malformed first response followed by a compliant second response succeeds
      and the returned
      value reflects the *second* response; a validator `ValueError` (valid
      JSON, wrong shape) is
      corrected on retry the same way a `JSONDecodeError` is; every attempt
      failing exhausts the
      budget and raises `LLMResponseError` naming `response_label` after exactly
      `max_correction_attempts + 1` total `chat()` calls; the corrective message
      sent on retry
      names the specific validation error, not a generic message; the request
      payload sent on
      every attempt (initial and corrective) uses the same plain
      `/chat/completions` shape as
      `chat()` already sends — no `response_format` or other added field

## 2. Migrate the three call sites

- [x] 2.1 `panopticon/drift.py`'s `check_drift()`: replace
      `complete_with_skill` + local `_strip_code_fence`/`json.loads`/try-except
      with
      `client.complete_json(..., validate=<moved stale/reasons type-check
      logic>,
      response_label="drift verdict", expected_shape="object")`; remove the
      now-dead local
      `_strip_code_fence` function
- [x] 2.2 `panopticon/currency.py`'s `check_currency()`: same migration, moving
  the
      current/reasons type-check logic into a `validate` callback,
      `response_label="index-currency verdict"`, `expected_shape="object"`;
      remove the local
      `_strip_code_fence`
- [x] 2.3 `panopticon/extraction.py`'s `llm_extract()`: same migration, moving
  the
      "must be a JSON array" check into a `validate` callback,
      `response_label="extraction
      response"`, `expected_shape="array"`; remove the local
      `_strip_code_fence`. Expanded the
      validator beyond the literal top-level-array check to also validate each
      item is an object
      with `raw_name`/`type`/`source_file` present — previously, a malformed
      item crashed with an
      *uncaught* `KeyError` outside any try/except (a pre-existing gap this
      change's "as robust as
      possible" goal covers); now a malformed item is corrected via the same
      retry path as a
      top-level shape problem. Also removed the now-unused `from .llm import
      LLMResponseError`
      import (nothing in this module raises or catches it directly anymore —
      `complete_json` does)
- [x] 2.4 Update `tests/test_drift.py`, `tests/test_currency.py`,
  `tests/test_extraction.py`.
      Implementation approach diverged from the literal task description: rather
      than editing each
      test file's `FakeClient`/stub separately, `tests/test_extraction.py`'s
      shared `FakeClient`
      (imported by all three test files) was reworked to delegate
      `complete_with_skill`/
      `complete_json` to the real `LLMClient` implementations bound to the fake
      (only `chat()`, the
      transport, is faked) — so tests exercise the actual retry logic, not a
      reimplementation of
      it. `FakeClient(response)` now also accepts a list of responses (consumed
      in order, last one
      repeats — mirroring `test_llm.py`'s `StubLLMServer` convention) for
      retry-then-succeed tests.
      Existing malformed-response tests needed **no changes at all**: a single
      string still repeats
      on every retry attempt automatically, so they already exercise the full
      retry-exhausted-then-fail-loudly path and still pass unchanged. Added one
      new
      `test_prose_first_response_recovers_on_retry` test per module
      (drift/currency/extraction)
      plus two extraction-specific tests for the new per-item validation
      (recovers on retry;
      eventually fails loudly) — all confirmed passing, plus the full 365-test
      suite

## 3. Documentation

- [x] 3.1 Update `docs/testing.md`'s rows for `tests/test_llm.py`,
  `tests/test_drift.py`,
      `tests/test_currency.py`, `tests/test_extraction.py` to describe the new
      retry coverage
- [x] 3.2 Update README.md and docs/spec.md to reflect any user-facing or
  architectural changes
      introduced by this change (this repo has no `docs/spec.md`; README.md's
      "Architecture
      principles" section updated to describe the shared `complete_json`
      corrective-retry
      contract)
