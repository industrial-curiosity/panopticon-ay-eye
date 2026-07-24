"""CI-only shared LLM runtime with LiteLLM HTTP and native Bedrock Converse adapters.

This module is the **CI execution path only** (design D5). Local flows — initialization, doc
updating, interface indexing — run the same skill files in the user's preferred agent harness and
never need ``PANOPTICON_LLM_*`` configuration.

The selected provider workflow maps instance-configured organization Actions names onto canonical
environment variables. LiteLLM uses:

- ``PANOPTICON_LLM_ENDPOINT`` — base URL of any litellm-compatible endpoint
  (``/chat/completions`` is appended if not already present); org-level **variable**
- ``PANOPTICON_LLM_API_KEY`` — bearer token for that endpoint; org-level **secret**
- ``PANOPTICON_LLM_MODEL`` — optional model name passed through to the endpoint; defaults to
  ``default`` (litellm proxies commonly route a default alias); org-level **variable**
- ``PANOPTICON_LLM_TIMEOUT_SECONDS`` — optional per-request timeout; defaults to ``90`` seconds
- ``PANOPTICON_LLM_MAX_ATTEMPTS`` — optional transport retry budget; defaults to ``2`` attempts
- ``PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS`` — optional JSON-correction retry budget; defaults
  to ``2`` retries

Bedrock uses ``PANOPTICON_AWS_REGION`` and ``PANOPTICON_LLM_MODEL`` after its workflow obtains
short-lived AWS credentials through OIDC. Both providers use the same bounded budget variables.

The shared prompting, structured validation, correction, and bounded retry behavior is provider-neutral.
LiteLLM remains standard-library HTTP. Bedrock lazily imports its pinned SDK only inside the Bedrock CI
workflow; child-vendored and local tooling never install it. Missing or unreachable requirements fail
loudly and LLM-dependent checks never silently skip or report success (agent-runtime spec).
"""

import json
import os
import time
import urllib.error
import urllib.request

ENDPOINT_VAR = "PANOPTICON_LLM_ENDPOINT"
API_KEY_VAR = "PANOPTICON_LLM_API_KEY"
MODEL_VAR = "PANOPTICON_LLM_MODEL"
TIMEOUT_VAR = "PANOPTICON_LLM_TIMEOUT_SECONDS"
MAX_ATTEMPTS_VAR = "PANOPTICON_LLM_MAX_ATTEMPTS"
MAX_CORRECTION_ATTEMPTS_VAR = "PANOPTICON_LLM_MAX_CORRECTION_ATTEMPTS"
PROVIDER_VAR = "PANOPTICON_LLM_PROVIDER"
AWS_REGION_VAR = "PANOPTICON_AWS_REGION"
DEFAULT_MODEL = "default"
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_MAX_CORRECTION_ATTEMPTS = 2

_REQUEST_BUDGETS = {
    TIMEOUT_VAR: (DEFAULT_TIMEOUT_SECONDS, 30, 300),
    MAX_ATTEMPTS_VAR: (DEFAULT_MAX_ATTEMPTS, 1, 3),
    MAX_CORRECTION_ATTEMPTS_VAR: (DEFAULT_MAX_CORRECTION_ATTEMPTS, 0, 2),
}

SETUP_HINT = (
    "Run the matching provider-specific Configure Panopticon workflow in the instance repo, "
    "configure the org-level Actions names it reports, and rerun child bootstrap so the caller "
    "maps those names explicitly (see docs/setup-guide.md in the Panopticon template repo)."
)

PURPOSES = {
    ENDPOINT_VAR: "base URL of the litellm-compatible LLM endpoint",
    API_KEY_VAR: "API key for the LLM endpoint",
    AWS_REGION_VAR: "AWS region containing the configured Bedrock model",
    MODEL_VAR: "provider model identifier",
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

    def __init__(self, endpoint, attempts, cause, provider="litellm"):
        self.endpoint = endpoint
        self.attempts = attempts
        self.cause = cause
        if provider == "bedrock":
            guidance = (
                f"Verify {AWS_REGION_VAR}, {MODEL_VAR}, the configured OIDC role, and its "
                "bedrock:InvokeModel permission."
            )
        else:
            guidance = (
                f"Verify {ENDPOINT_VAR} points at a reachable litellm-compatible endpoint and "
                f"{API_KEY_VAR} is valid."
            )
        super().__init__(
            f"{provider} LLM request to {endpoint} failed after {attempts} attempt(s): "
            f"{cause}. {guidance}"
        )


class LLMResponseError(Exception):
    """The endpoint answered, but not with a usable chat completion."""


class LLMConfigurationError(Exception):
    """An optional LLM runtime setting is malformed or outside its safe range."""


def _request_budget_from_env(name, env):
    """Read one bounded integer runtime setting, retaining its default when unset."""
    default, minimum, maximum = _REQUEST_BUDGETS[name]
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = int(raw, 10)
    except (TypeError, ValueError):
        value = None
    if value is None or not minimum <= value <= maximum:
        raise LLMConfigurationError(
            f"invalid {name}: expected an integer from {minimum} through {maximum}; got {raw!r}"
        )
    return value


def _strip_code_fence(text):
    """Strip a wrapping markdown code fence (```...```) if the whole response is fenced. Shared by
    every structured-response call site (design D1) — previously duplicated identically in
    drift.py/currency.py/extraction.py."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[-1].strip().startswith("```"):
            return "\n".join(lines[1:-1])
    return text


class LiteLLMAdapter:
    """OpenAI-compatible HTTP transport; shared prompting and correction stay in LLMClient."""

    def __init__(self, endpoint, api_key, model=DEFAULT_MODEL, timeout=DEFAULT_TIMEOUT_SECONDS,
                 max_attempts=DEFAULT_MAX_ATTEMPTS, sleep=time.sleep):
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

    def preflight(self):
        return {"provider": "litellm", "endpoint": self.endpoint, "model": self.model}

    def chat(self, messages, temperature=0):
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


class LLMClient:
    def __init__(self, endpoint, api_key, model=DEFAULT_MODEL, timeout=DEFAULT_TIMEOUT_SECONDS,
                 max_attempts=DEFAULT_MAX_ATTEMPTS,
                 max_correction_attempts=DEFAULT_MAX_CORRECTION_ATTEMPTS, sleep=time.sleep):
        self._adapter = LiteLLMAdapter(endpoint, api_key, model, timeout, max_attempts, sleep)
        self.endpoint = self._adapter.endpoint
        self.api_key = self._adapter.api_key
        self.model = self._adapter.model
        self.timeout = self._adapter.timeout
        self.max_attempts = self._adapter.max_attempts
        self.max_correction_attempts = max_correction_attempts

    @classmethod
    def from_env(cls, env=os.environ, **kwargs):
        if cls is LLMClient:
            provider = env.get(PROVIDER_VAR, "litellm")
            if provider == "bedrock":
                return BedrockLLMClient.from_env(env, **kwargs)
            if provider != "litellm":
                raise LLMConfigurationError(
                    f"invalid {PROVIDER_VAR}: expected 'litellm' or 'bedrock'; got {provider!r}"
                )
        request_budget = {
            "timeout": _request_budget_from_env(TIMEOUT_VAR, env),
            "max_attempts": _request_budget_from_env(MAX_ATTEMPTS_VAR, env),
            "max_correction_attempts": _request_budget_from_env(MAX_CORRECTION_ATTEMPTS_VAR, env),
        }
        request_budget.update(kwargs)
        return cls(
            endpoint=env.get(ENDPOINT_VAR),
            api_key=env.get(API_KEY_VAR),
            model=env.get(MODEL_VAR, DEFAULT_MODEL),
            **request_budget,
        )

    def preflight(self):
        """Validate mapped LiteLLM configuration without making a billable inference request."""
        return self._adapter.preflight()

    def chat(self, messages, temperature=0):
        """POST a chat completion; returns the first choice's message content."""
        return self._adapter.chat(messages, temperature)

    def complete_with_skill(self, skill_text, user_content, temperature=0):
        """Chat with a skill file's content as the system prompt (skill-based prompting)."""
        return self.chat(
            [
                {"role": "system", "content": skill_text},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
        )

    def complete_json(self, skill_text, user_content, validate, *, response_label,
                       expected_shape="object", temperature=0, max_correction_attempts=None):
        """Chat with a skill file's content as the system prompt, expecting a strict JSON response
        (agent-runtime spec: "Structured-response retry for non-compliant model output").

        ``validate(parsed)`` SHALL raise ``ValueError`` (with a message naming the specific
        problem) if ``parsed`` doesn't match the caller's expected shape; otherwise it returns
        None and ``parsed`` is returned as-is. On a parse failure (not valid JSON, possibly wrapped
        in a markdown code fence) or a ``validate`` failure, the model's non-compliant response is
        appended to the conversation as an assistant turn, followed by a corrective user turn
        naming the specific error and restating the response contract, and the whole conversation
        is retried — up to ``max_correction_attempts`` additional times — before raising
        ``LLMResponseError`` naming ``response_label``. This never relaxes validation: a response
        that fails ``validate`` is corrected via retry, never silently accepted.
        """
        if max_correction_attempts is None:
            max_correction_attempts = self.max_correction_attempts
        messages = [
            {"role": "system", "content": skill_text},
            {"role": "user", "content": user_content},
        ]
        last_error = None
        last_response = None
        for attempt in range(max_correction_attempts + 1):
            response = self.chat(messages, temperature=temperature)
            last_response = response
            try:
                parsed = json.loads(_strip_code_fence(response))
                validate(parsed)
                return parsed
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt < max_correction_attempts:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Your previous response was not valid JSON matching the required "
                            f"shape ({exc}). Respond with ONLY the JSON {expected_shape} — no "
                            f"prose, no code fences, no explanation."
                        ),
                    })
        raise LLMResponseError(
            f"{response_label} is not the expected JSON shape after "
            f"{max_correction_attempts + 1} attempt(s) ({last_error}): {last_response[:500]!r}"
        )


class BedrockLLMClient(LLMClient):
    """AWS Bedrock Converse adapter using credentials established by GitHub OIDC."""

    _RETRYABLE_CODES = {
        "InternalServerException",
        "ModelNotReadyException",
        "ServiceUnavailableException",
        "ThrottlingException",
    }

    def __init__(self, region, model, timeout=DEFAULT_TIMEOUT_SECONDS,
                 max_attempts=DEFAULT_MAX_ATTEMPTS,
                 max_correction_attempts=DEFAULT_MAX_CORRECTION_ATTEMPTS, sleep=time.sleep,
                 runtime_client=None, boto3_module=None, client_config_factory=None):
        missing = [name for name, value in ((AWS_REGION_VAR, region), (MODEL_VAR, model)) if not value]
        if missing:
            raise MissingRequirementError(missing)
        self.region = region
        self.model = model
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.max_correction_attempts = max_correction_attempts
        self._sleep = sleep
        self._runtime_client = runtime_client
        self._boto3_module = boto3_module
        self._client_config_factory = client_config_factory

    @classmethod
    def from_env(cls, env=os.environ, **kwargs):
        request_budget = {
            "timeout": _request_budget_from_env(TIMEOUT_VAR, env),
            "max_attempts": _request_budget_from_env(MAX_ATTEMPTS_VAR, env),
            "max_correction_attempts": _request_budget_from_env(MAX_CORRECTION_ATTEMPTS_VAR, env),
        }
        request_budget.update(kwargs)
        return cls(
            region=env.get(AWS_REGION_VAR),
            model=env.get(MODEL_VAR),
            **request_budget,
        )

    def _load_runtime(self):
        if self._runtime_client is None:
            try:
                if self._boto3_module is None:
                    try:
                        import boto3
                    except ImportError as exc:
                        raise LLMConfigurationError(
                            "Bedrock provider requires the pinned CI-only boto3 dependency; "
                            "install requirements-bedrock.txt in the Bedrock workflow"
                        ) from exc
                    self._boto3_module = boto3
                if self._client_config_factory is None:
                    from botocore.config import Config
                    self._client_config_factory = Config
                client_config = self._client_config_factory(
                    connect_timeout=self.timeout,
                    read_timeout=self.timeout,
                    retries={"max_attempts": 0},
                )
                self._runtime_client = self._boto3_module.client(
                    "bedrock-runtime", region_name=self.region, config=client_config
                )
            except Exception as exc:
                raise LLMConfigurationError(
                    f"could not construct the Bedrock runtime client in {self.region}: {exc}"
                ) from exc
        return self._runtime_client

    def preflight(self):
        """Verify the pinned SDK and runtime client expose Bedrock Converse."""
        runtime = self._load_runtime()
        version = getattr(self._boto3_module, "__version__", "unknown")
        import_path = getattr(self._boto3_module, "__file__", "unknown")
        if not callable(getattr(runtime, "converse", None)):
            raise LLMConfigurationError(
                "Bedrock runtime lacks Converse support; resolved "
                f"boto3 {version} from {import_path}. Reinstall the exact dependency from "
                "requirements-bedrock.txt in the Bedrock workflow."
            )
        return {
            "provider": "bedrock",
            "model": self.model,
            "region": self.region,
            "boto3_version": version,
            "boto3_path": import_path,
        }

    @staticmethod
    def _messages_for_converse(messages):
        system = []
        conversation = []
        for message in messages:
            block = {"text": message["content"]}
            if message["role"] == "system":
                system.append(block)
            else:
                conversation.append({"role": message["role"], "content": [block]})
        return system, conversation

    @staticmethod
    def _error_code(exc):
        response = getattr(exc, "response", {})
        return response.get("Error", {}).get("Code") or type(exc).__name__

    def chat(self, messages, temperature=0):
        runtime = self._load_runtime()
        system, conversation = self._messages_for_converse(messages)
        resource = f"bedrock://{self.region}/{self.model}"
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            request = {
                "modelId": self.model,
                "messages": conversation,
                "inferenceConfig": {"temperature": temperature},
            }
            if system:
                request["system"] = system
            try:
                response = runtime.converse(**request)
                blocks = response["output"]["message"]["content"]
                content = "".join(block["text"] for block in blocks if "text" in block)
                if not content:
                    raise LLMResponseError(
                        f"Bedrock Converse returned no text content: {response!r}"
                    )
                return content
            except LLMResponseError:
                raise
            except Exception as exc:
                code = self._error_code(exc)
                last_error = f"{code}: {exc}"
                if code not in self._RETRYABLE_CODES:
                    raise LLMRequestError(resource, attempt, last_error, provider="bedrock")
            if attempt < self.max_attempts:
                self._sleep(2 ** (attempt - 1))
        raise LLMRequestError(resource, self.max_attempts, last_error, provider="bedrock")


def require(names=(ENDPOINT_VAR, API_KEY_VAR), env=os.environ, purposes=None):
    """Fail loudly, listing *every* missing CI requirement at once (not just the first)."""
    missing = [name for name in names if not env.get(name)]
    if missing:
        raise MissingRequirementError(missing, {**PURPOSES, **(purposes or {})})
