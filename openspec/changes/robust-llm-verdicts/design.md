## Context

`panopticon/llm.py`'s `LLMClient` is a thin, provider-agnostic HTTP client for any litellm-compatible
`/chat/completions` endpoint (agent-runtime spec: "Provider-agnostic LLM configuration for CI"). It
already retries transport-level failures (429/5xx, exponential backoff, `LLMRequestError` after
exhausting attempts). What it has never had is any recovery for a *successful* HTTP response whose
content doesn't match the structured-output contract a skill's system prompt demands.

Three call sites independently re-implement the same brittle pattern, confirmed by reading each in full:

- `panopticon/drift.py`'s `check_drift()` — expects `{"stale": bool, "reasons": [...], "summary": str}`
- `panopticon/currency.py`'s `check_currency()` — expects `{"current": bool, "reasons": [...], "summary": str}`
- `panopticon/extraction.py`'s `llm_extract()` — expects a JSON array of candidate objects

Each: calls `client.complete_with_skill(...)`, strips a markdown code fence via its own copy of an
identical `_strip_code_fence()` helper, calls `json.loads()` once, does some ad-hoc field-type
checking, and raises `LLMResponseError` immediately on any failure. A real CI run hit this: the
configured model answered a doc-drift check with prose reasoning instead of JSON, `check_drift()`
raised on the first and only parse attempt, and the check failed with no recovery path.

## Goals / Non-Goals

**Goals:**

- One shared, hardened implementation of "ask for structured JSON, validate it, recover from
  non-compliant output" that all three call sites use — not three independently-drifting copies.
- Recover from a model that doesn't comply with "respond with only JSON" on the first attempt, via
  bounded corrective re-prompting, before failing loudly.
- Preserve the existing "malformed responses are loud errors, never a silent pass" discipline
  (already stated in `drift.py`'s own module docstring) — retries correct the model's output, they
  never relax what counts as valid.
- Work across "a wide variety of LLMs" (explicit user requirement) without provider-specific code
  paths — Panopticon's whole design premise is any litellm-compatible endpoint works.

**Non-Goals:**

- Not adding `response_format`/JSON-mode API parameters. Not every litellm-compatible provider
  supports this uniformly, and some reject unrecognized request fields outright — adding it risks
  breaking providers that currently work, in service of a feature that wouldn't fully solve the
  problem anyway (reasoning models can still emit prose even in "JSON mode" on some providers).
- Not changing the exit-code contract (0/2/operational-failure) of `drift.py`/`currency.py`, or
  `extraction.py`'s `main()` always-0 contract. This is purely about getting a valid verdict more
  reliably, not changing what a verdict means.
- Not adding a general-purpose prompt-engineering framework. The fix is narrowly scoped to the
  parse-validate-retry loop around structured JSON responses.

## Decisions

### D1: One shared `LLMClient.complete_json()` method, not three independently-hardened call sites

**Decision**: add `complete_json(skill_text, user_content, validate, *, expected_shape, temperature=0)`
to `LLMClient`. It owns: sending the skill-based chat request, stripping code fences, `json.loads`,
calling the caller-supplied `validate(parsed)` (raises `ValueError` on a shape problem), the
corrective-retry loop (D2), and raising `LLMResponseError` with a clear message once the retry budget
is exhausted. `drift.py`, `currency.py`, and `extraction.py` each pass their own small `validate`
callback (already-existing field-type-checking logic, moved as-is) and use the shared method instead
of `complete_with_skill` + their own `_strip_code_fence`/`json.loads`/try-except block. The `_strip_code_fence`
helper — currently defined identically three times — moves into `llm.py` as a private function.

*Alternative considered*: keep three separate implementations, just add retry logic to each
independently. Rejected — this is exactly how the current triplication (each a slightly-diverging
copy of `_strip_code_fence`) happened in the first place; a bug fixed in one copy silently doesn't
apply to the other two. One implementation, three thin call sites.

### D2: Bounded corrective retry via appended conversation turns, not a fresh request

**Decision**: on a parse/validation failure, `complete_json` appends the model's own non-compliant
response as an `assistant` turn, then appends a `user` turn stating plainly what was wrong and
restating the contract ("Your previous response was not valid JSON matching the required shape
(`<the ValueError's message>`). Respond with ONLY the JSON `<object|array>` — no prose, no code
fences, no explanation.") — then re-sends the *whole* conversation (system skill prompt + original
user content + the failed attempt + the correction) as a new `chat()` call. Default: 2 correction
attempts (3 total LLM calls), mirroring the existing HTTP-retry precedent's `max_attempts=3`.
Configurable via a constructor/method parameter (tests inject a lower bound to keep fixtures small).

Showing the model its own bad output plus a specific correction is more effective than a blind
identical retry (which would likely reproduce the same non-compliant response) — this directly
targets what actually went wrong (a reasoning model narrating instead of answering), without
depending on any provider-specific capability.

*Alternative considered*: blind retry (resend the identical original request, hoping for a
different sample). Rejected — with `temperature=0` (this codebase's default for verdict/extraction
calls, confirmed in each call site), most providers return the same or a near-identical response
deterministically; a blind retry would likely just fail the same way again, wasting a request.

*Alternative considered*: an unbounded retry loop. Rejected — matches this codebase's existing
"always bounded, then fail loudly" discipline (HTTP retries cap at `max_attempts`); an unbounded
loop against a systematically non-compliant model or misconfigured endpoint would hang CI instead
of failing with an actionable error.

### D3: No `response_format`/JSON-mode enforcement

**Decision**: `complete_json` does not add `response_format: {"type": "json_object"}` or any
provider-specific structured-output parameter to the request payload. See Non-Goals — this is a
deliberate scope boundary, not an oversight.

*Alternative considered*: add `response_format` when present in a config flag, off by default.
Rejected as unnecessary complexity for a currently-unconfirmed benefit — corrective retry (D2)
already directly addresses the failure mode actually observed (a reasoning model narrating), and
adding an optional, provider-dependent parameter that most users would never discover or enable
doesn't pull its weight against that.

### D4: Validator-callback pattern preserves per-call-site error framing

**Decision**: `complete_json` takes a `validate(parsed) -> None` callback (raising `ValueError` with
a specific message on a shape problem) rather than a fixed schema-description parameter. Each call
site keeps its existing, specific validation logic (e.g. drift's `stale` must be `bool`, extraction's
top-level value must be a `list`) verbatim, just relocated into a small function passed to
`complete_json`. The final `LLMResponseError` message includes a caller-supplied `response_label`
(e.g. `"drift verdict"`, `"index-currency verdict"`, `"extraction response"`) so operational-failure
messages stay exactly as specific as they are today, not generic across all three checks.

## Risks / Trade-offs

- **[Risk]** Corrective retry means a persistently non-compliant model now costs up to 3x the LLM
  calls (latency, and cost if the endpoint is metered) before failing, instead of failing fast on
  the first bad response. → **Mitigation**: bounded at a small default (2 extra attempts); this is
  the same trade-off the existing HTTP-retry logic already accepts for transport failures, and a
  check that now *succeeds* on attempt 2 instead of failing outright is a strict improvement over
  today's zero-recovery behavior.
- **[Risk]** `temperature=0` retries could still reproduce the identical non-compliant response if a
  provider's determinism means the correction message doesn't change anything about how the model
  reasons. → **Mitigation**: none needed at the retry-loop level — this degrades gracefully to
  today's exact behavior (fail loudly after the budget is exhausted), just with the same number of
  extra attempts as any other non-compliant case. Not worse than today, sometimes better.
- **[Trade-off]** Consolidating three call sites onto one shared method is a larger diff than
  patching each independently, touching tests in three modules plus `llm.py`. Accepted — this is
  exactly the "as robust as possible" ask, and per-module patches would re-introduce the
  duplication risk D1 addresses.

## Migration Plan

1. Add `complete_json` (and the relocated `_strip_code_fence`) to `llm.py`, fully unit-tested in
   isolation (retry-then-succeed, retry-exhausted-then-fail-loudly, validator errors surfaced
   correctly) — no other module touched yet.
2. Migrate `drift.py`, `currency.py`, `extraction.py` one at a time onto `complete_json`, removing
   each one's own `_strip_code_fence` and inline parse/validate block, updating that module's tests
   to account for retry (existing single-canned-response fakes need to support returning multiple
   responses in sequence).
3. Rollback: each of the four steps (shared method, then each of the three migrations) is
   independently revertable — no schema change, no data migration, no change to any check's
   exit-code contract.

## Open Questions

- Exact default for `max_correction_attempts` (2 extra / 3 total proposed here, mirroring the HTTP
  retry precedent) — settle finally in tasks.md if a different number turns out to read better
  against real skill files during implementation.
