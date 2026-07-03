"""CI-only LLM runtime: a thin stdlib HTTP client for OpenAI-compatible ``/chat/completions``.

This module is the **CI execution path only** (design D5). Local flows — initialization, doc
updating, interface indexing — run the same skill files in the user's preferred agent harness and
never need ``PANOPTICON_LLM_*`` configuration.

Configuration comes from org-level secrets exposed as environment variables:

- ``PANOPTICON_LLM_ENDPOINT`` — base URL of any litellm-compatible endpoint
  (``/chat/completions`` is appended if not already present)
- ``PANOPTICON_LLM_API_KEY`` — bearer token for that endpoint
- ``PANOPTICON_LLM_MODEL`` — optional model name passed through to the endpoint; defaults to
  ``default`` (litellm proxies commonly route a default alias)

No provider SDKs, no agent frameworks, no provider-specific code paths. Missing or unreachable
requirements fail loudly (``MissingRequirementError`` / ``LLMRequestError``) naming exactly what
is missing and how to provide it — LLM-dependent checks must never silently skip or report
success (agent-runtime spec).
"""

import json
import os
import time
import urllib.error
import urllib.request

ENDPOINT_VAR = "PANOPTICON_LLM_ENDPOINT"
API_KEY_VAR = "PANOPTICON_LLM_API_KEY"
MODEL_VAR = "PANOPTICON_LLM_MODEL"
DEFAULT_MODEL = "default"

SETUP_HINT = (
    "Configure it as an org-level GitHub Actions secret so every child repo inherits it "
    "(see docs/setup-guide.md in the Panopticon template repo). Child repos never configure "
    "per-repo secrets."
)

PURPOSES = {
    ENDPOINT_VAR: "base URL of the litellm-compatible LLM endpoint",
    API_KEY_VAR: "API key for the LLM endpoint",
    "PANOPTICON_INSTANCE_TOKEN": "fine-grained PAT with contents read/write and issues write on the instance repo",
}

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class MissingRequirementError(Exception):
    """A required piece of CI configuration is absent; the workflow must fail loudly."""

    def __init__(self, names, purposes=None):
        self.names = [names] if isinstance(names, str) else list(names)
        purposes = purposes or {}
        described = ", ".join(
            f"{name} ({purposes[name]})" if name in purposes else name for name in self.names
        )
        noun = "requirement" if len(self.names) == 1 else "requirements"
        super().__init__(f"missing {noun}: {described} not set. {SETUP_HINT}")


class LLMRequestError(Exception):
    """The endpoint could not complete the request after retries."""

    def __init__(self, endpoint, attempts, cause):
        self.endpoint = endpoint
        self.attempts = attempts
        self.cause = cause
        super().__init__(
            f"LLM request to {endpoint} failed after {attempts} attempt(s): {cause}. "
            f"Verify {ENDPOINT_VAR} points at a reachable litellm-compatible endpoint and "
            f"{API_KEY_VAR} is valid."
        )


class LLMResponseError(Exception):
    """The endpoint answered, but not with a usable chat completion."""


class LLMClient:
    def __init__(self, endpoint, api_key, model=DEFAULT_MODEL, timeout=60, max_attempts=3, sleep=time.sleep):
        missing = [name for name, value in ((ENDPOINT_VAR, endpoint), (API_KEY_VAR, api_key)) if not value]
        if missing:
            raise MissingRequirementError(missing, PURPOSES)
        endpoint = endpoint.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_attempts = max_attempts
        self._sleep = sleep

    @classmethod
    def from_env(cls, env=os.environ, **kwargs):
        return cls(
            endpoint=env.get(ENDPOINT_VAR),
            api_key=env.get(API_KEY_VAR),
            model=env.get(MODEL_VAR, DEFAULT_MODEL),
            **kwargs,
        )

    def chat(self, messages, temperature=0):
        """POST a chat completion; returns the first choice's message content."""
        payload = json.dumps(
            {"model": self.model, "messages": messages, "temperature": temperature}
        ).encode("utf-8")
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            request = urllib.request.Request(
                self.endpoint,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return self._parse_response(response.read())
            except urllib.error.HTTPError as exc:
                with exc:
                    last_error = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}"
                if exc.code not in _RETRYABLE_STATUS:
                    raise LLMRequestError(self.endpoint, attempt, last_error)
            except urllib.error.URLError as exc:
                last_error = f"connection failed: {exc.reason}"
            except TimeoutError:
                last_error = f"timed out after {self.timeout}s"
            if attempt < self.max_attempts:
                self._sleep(2 ** (attempt - 1))
        raise LLMRequestError(self.endpoint, self.max_attempts, last_error)

    @staticmethod
    def _parse_response(body):
        try:
            doc = json.loads(body)
            content = doc["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError(
                f"endpoint returned an unexpected response shape ({exc}): {body[:500]!r}"
            )
        if not isinstance(content, str):
            raise LLMResponseError(f"completion content is not text: {content!r}")
        return content

    def complete_with_skill(self, skill_text, user_content, temperature=0):
        """Chat with a skill file's content as the system prompt (skill-based prompting)."""
        return self.chat(
            [
                {"role": "system", "content": skill_text},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
        )


def require(names=(ENDPOINT_VAR, API_KEY_VAR), env=os.environ, purposes=None):
    """Fail loudly, listing *every* missing CI requirement at once (not just the first)."""
    missing = [name for name in names if not env.get(name)]
    if missing:
        raise MissingRequirementError(missing, {**PURPOSES, **(purposes or {})})
