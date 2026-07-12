## Why

A real CI failure exposed a brittleness gap: the configured model responded to a doc-drift check with
prose reasoning ("Looking at this PR diff carefully, I need to determine...") instead of the JSON verdict
the `panopticon-doc-drift` skill's response contract requires. `panopticon/drift.py`'s `check_drift()`
had no recovery path — it parsed the raw response with `json.loads()`, the parse failed, and the whole
check crashed with an operational failure. Investigation confirmed this is not isolated: `currency.py`'s
`check_currency()` and `extraction.py`'s `llm_extract()` share the identical brittle pattern (duplicated
independently in each module), and `panopticon/llm.py`'s `LLMClient` has no application-level recovery for
non-compliant model output — only HTTP-level retries for transport failures. Panopticon is explicitly
provider-agnostic (any litellm-compatible endpoint), so this gap will recur with any model that doesn't
reliably suppress reasoning/prose even when a skill's response contract says "respond with only JSON."

## What Changes

- `panopticon/llm.py`'s `LLMClient` gains a single shared, hardened structured-response method (e.g.
  `complete_json`) that all three verdict/extraction call sites use, replacing each module's own
  independently-duplicated `_strip_code_fence` + `json.loads` + ad-hoc shape validation.
- When a response fails to parse as JSON or fails shape validation, the runtime SHALL retry with an
  explicit corrective message appended to the conversation (e.g. "Your previous response was not valid
  JSON matching the required shape. Respond with ONLY the JSON object/array, no prose, no code fences.")
  for a small bounded number of attempts before failing loudly. This is corrective re-prompting, not
  relaxed validation — the existing "malformed responses are loud errors, never a silent pass" discipline
  (already stated in `drift.py`'s own module docstring) is preserved and now applies uniformly across all
  three call sites via the shared implementation.
- `panopticon/drift.py`'s `check_drift()`, `panopticon/currency.py`'s `check_currency()`, and
  `panopticon/extraction.py`'s `llm_extract()` are migrated onto the shared method, removing their
  individual duplicated parsing/validation logic.
- No `response_format`/JSON-mode API parameter is added — deliberately: not every litellm-compatible
  provider supports it uniformly, and Panopticon's explicit design goal is working with "a wide variety
  of LLMs" without provider-specific code paths. Robustness comes from corrective re-prompting at the
  application level instead, which any reasonably capable model can act on regardless of provider.

## Capabilities

### New Capabilities

(none — this hardens existing behavior)

### Modified Capabilities

- `agent-runtime`: the runtime's response-handling contract gains an explicit, bounded corrective-retry
  requirement for non-compliant structured output, replacing the current all-or-nothing "parse once, fail
  loudly" behavior implied by (but not explicitly specified in) the existing "Fail loudly on missing
  requirements" requirement. The loud-failure guarantee itself is preserved — it now applies only after
  the retry budget is exhausted.

## Impact

- **Code**: `panopticon/llm.py` (new shared `complete_json`-style method on `LLMClient`), `panopticon/drift.py`,
  `panopticon/currency.py`, `panopticon/extraction.py` (migrated to the shared method; their own
  `_strip_code_fence`/parsing logic removed).
- **Skills**: `.agents/skills/panopticon-doc-drift`, `panopticon-index-currency`,
  `panopticon-interface-extraction` — response-contract wording reviewed for clarity but not restructured;
  the fix is primarily in the runtime's retry behavior, not the prompts themselves.
- **Tests**: `tests/test_llm.py` gains coverage for the new shared method's retry-then-succeed and
  retry-exhausted-then-fail-loudly paths; `tests/test_drift.py`, `tests/test_currency.py`,
  `tests/test_extraction.py` updated for the migration.
- **No breaking changes**: purely additive robustness. Exit-code contracts (0/2/operational-failure) for
  all three checks are unchanged; only the number of LLM round-trips before either succeeding or failing
  loudly can now be greater than one.
