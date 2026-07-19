"""Agent runtime: request shape, retries, and fail-loudly degradation paths, via a stub server."""

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from panopticon.llm import (
    API_KEY_VAR,
    AWS_REGION_VAR,
    BedrockLLMClient,
    ENDPOINT_VAR,
    MAX_ATTEMPTS_VAR,
    MAX_CORRECTION_ATTEMPTS_VAR,
    LLMClient,
    LLMConfigurationError,
    LLMRequestError,
    LLMResponseError,
    LiteLLMAdapter,
    MissingRequirementError,
    MODEL_VAR,
    PROVIDER_VAR,
    TIMEOUT_VAR,
    require,
)
from panopticon.skills import SkillNotFoundError, load_skill, strip_frontmatter


class StubLLMServer:
    """In-process /chat/completions endpoint with a scriptable response queue."""

    def __init__(self):
        self.requests = []
        self.responses = []  # queue of (status, body_dict_or_str); last one repeats
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                stub.requests.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "content_type": self.headers.get("Content-Type"),
                        "body": json.loads(self.rfile.read(length)),
                    }
                )
                status, body = stub.responses[min(len(stub.requests), len(stub.responses)) - 1]
                payload = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    @property
    def endpoint(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"


def completion(content):
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def client_for(stub, **kwargs):
    kwargs.setdefault("sleep", lambda seconds: None)
    return LLMClient(stub.endpoint, api_key="test-key", model="test-model", **kwargs)


class TestRequestShape(unittest.TestCase):
    def test_openai_compatible_request(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, completion("hello"))]
            result = client_for(stub).chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result, "hello")
        (request,) = stub.requests
        self.assertEqual(request["path"], "/v1/chat/completions")
        self.assertEqual(request["authorization"], "Bearer test-key")
        self.assertEqual(request["content_type"], "application/json")
        self.assertEqual(
            request["body"],
            {"model": "test-model", "messages": [{"role": "user", "content": "hi"}], "temperature": 0},
        )

    def test_skill_text_becomes_system_prompt(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, completion("ok"))]
            client_for(stub).complete_with_skill("You are the drift checker.", "diff here")
        messages = stub.requests[0]["body"]["messages"]
        self.assertEqual(messages[0], {"role": "system", "content": "You are the drift checker."})
        self.assertEqual(messages[1]["role"], "user")

    def test_endpoint_already_ending_in_chat_completions_is_not_doubled(self):
        client = LLMClient("http://example.test/v1/chat/completions", api_key="k")
        self.assertEqual(client.endpoint, "http://example.test/v1/chat/completions")

    def test_litellm_preflight_does_not_send_a_request(self):
        with StubLLMServer() as stub:
            details = client_for(stub).preflight()
        self.assertEqual(details["provider"], "litellm")
        self.assertEqual(stub.requests, [])
        self.assertIsInstance(client_for(stub)._adapter, LiteLLMAdapter)

    def test_pr_workflow_exposes_the_llm_request_budget(self):
        workflows = Path(__file__).resolve().parent.parent / ".github" / "workflows"
        for provider in ("litellm", "bedrock"):
            workflow = (workflows / f"panopticon-pr-{provider}.yml").read_text()
            self.assertIn(
                "fromJSON(inputs.job_timeout_minutes || '20') >= 10",
                workflow,
            )
            self.assertIn("fromJSON(inputs.job_timeout_minutes || '20') <= 60", workflow)
            for name in (TIMEOUT_VAR, MAX_ATTEMPTS_VAR, MAX_CORRECTION_ATTEMPTS_VAR):
                self.assertIn(name, workflow)


class TestRetries(unittest.TestCase):
    def test_retries_on_5xx_then_succeeds(self):
        with StubLLMServer() as stub:
            stub.responses = [(503, "busy"), (200, completion("recovered"))]
            result = client_for(stub).chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result, "recovered")
        self.assertEqual(len(stub.requests), 2)

    def test_exhausted_retries_fail_loudly(self):
        with StubLLMServer() as stub:
            stub.responses = [(503, "busy")]
            with self.assertRaises(LLMRequestError) as ctx:
                client_for(stub, max_attempts=2).chat([{"role": "user", "content": "hi"}])
        self.assertEqual(len(stub.requests), 2)
        self.assertIn("failed after 2 attempt(s)", str(ctx.exception))
        self.assertIn(ENDPOINT_VAR, str(ctx.exception))

    def test_non_retryable_http_error_fails_immediately(self):
        with StubLLMServer() as stub:
            stub.responses = [(401, "bad key")]
            with self.assertRaises(LLMRequestError):
                client_for(stub).chat([{"role": "user", "content": "hi"}])
        self.assertEqual(len(stub.requests), 1)

    def test_unreachable_endpoint_fails_loudly(self):
        client = LLMClient(
            "http://127.0.0.1:1/v1", api_key="k", max_attempts=2, timeout=1, sleep=lambda s: None
        )
        with self.assertRaises(LLMRequestError) as ctx:
            client.chat([{"role": "user", "content": "hi"}])
        self.assertIn("connection failed", str(ctx.exception))


class TestDegradationPaths(unittest.TestCase):
    def test_request_budget_defaults_are_applied_from_environment(self):
        client = LLMClient.from_env(env={ENDPOINT_VAR: "http://example.test", API_KEY_VAR: "key"})
        self.assertEqual(client.timeout, 90)
        self.assertEqual(client.max_attempts, 2)
        self.assertEqual(client.max_correction_attempts, 2)

    def test_request_budget_overrides_are_applied_from_environment(self):
        client = LLMClient.from_env(env={
            ENDPOINT_VAR: "http://example.test", API_KEY_VAR: "key",
            TIMEOUT_VAR: "120", MAX_ATTEMPTS_VAR: "3", MAX_CORRECTION_ATTEMPTS_VAR: "1",
        })
        self.assertEqual(client.timeout, 120)
        self.assertEqual(client.max_attempts, 3)
        self.assertEqual(client.max_correction_attempts, 1)

    def test_explicit_constructor_overrides_win_over_environment_budget(self):
        client = LLMClient.from_env(
            env={ENDPOINT_VAR: "http://example.test", API_KEY_VAR: "key", TIMEOUT_VAR: "120"},
            timeout=30,
        )
        self.assertEqual(client.timeout, 30)

    def test_invalid_request_budget_values_fail_before_client_creation(self):
        cases = (
            (TIMEOUT_VAR, "five", "30 through 300"),
            (TIMEOUT_VAR, "29", "30 through 300"),
            (MAX_ATTEMPTS_VAR, "", "1 through 3"),
            (MAX_ATTEMPTS_VAR, "4", "1 through 3"),
            (MAX_CORRECTION_ATTEMPTS_VAR, "-1", "0 through 2"),
            (MAX_CORRECTION_ATTEMPTS_VAR, "3", "0 through 2"),
        )
        for name, value, permitted_range in cases:
            with self.subTest(name=name, value=value), self.assertRaises(LLMConfigurationError) as ctx:
                LLMClient.from_env(env={ENDPOINT_VAR: "http://example.test", API_KEY_VAR: "key", name: value})
            self.assertIn(name, str(ctx.exception))
            self.assertIn(permitted_range, str(ctx.exception))

    def test_missing_configuration_names_every_missing_variable(self):
        with self.assertRaises(MissingRequirementError) as ctx:
            LLMClient.from_env(env={})
        message = str(ctx.exception)
        self.assertIn(ENDPOINT_VAR, message)
        self.assertIn(API_KEY_VAR, message)
        self.assertIn("org-level", message)

    def test_require_lists_missing_requirements(self):
        with self.assertRaises(MissingRequirementError) as ctx:
            require((ENDPOINT_VAR, API_KEY_VAR, "PANOPTICON_INSTANCE_TOKEN"), env={ENDPOINT_VAR: "x"})
        exc = ctx.exception
        self.assertNotIn(ENDPOINT_VAR, exc.names)
        self.assertIn(API_KEY_VAR, exc.names)
        self.assertIn("PANOPTICON_INSTANCE_TOKEN", exc.names)

    def test_unknown_provider_fails_before_client_creation(self):
        with self.assertRaisesRegex(LLMConfigurationError, PROVIDER_VAR):
            LLMClient.from_env(env={PROVIDER_VAR: "unknown"})

    def test_malformed_response_is_a_loud_error(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, {"unexpected": True})]
            with self.assertRaises(LLMResponseError):
                client_for(stub).chat([{"role": "user", "content": "hi"}])


def _validate_stale_shape(parsed):
    if not isinstance(parsed, dict) or not isinstance(parsed.get("stale"), bool):
        raise ValueError("'stale' must be a boolean")


class TestCompleteJson(unittest.TestCase):
    def test_first_attempt_success_no_retry(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, completion(json.dumps({"stale": True})))]
            result = client_for(stub).complete_json(
                "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
            )
        self.assertEqual(result, {"stale": True})
        self.assertEqual(len(stub.requests), 1)


    def test_malformed_first_response_corrected_on_retry(self):
        with StubLLMServer() as stub:
            stub.responses = [
                (200, completion("Looking at this diff carefully, I need to determine...")),
                (200, completion(json.dumps({"stale": False}))),
            ]
            result = client_for(stub).complete_json(
                "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
            )
        self.assertEqual(result, {"stale": False})
        self.assertEqual(len(stub.requests), 2)

    def test_validator_failure_is_corrected_on_retry_same_as_parse_failure(self):
        with StubLLMServer() as stub:
            stub.responses = [
                (200, completion(json.dumps({"stale": "not-a-bool"}))),
                (200, completion(json.dumps({"stale": True}))),
            ]
            result = client_for(stub).complete_json(
                "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
            )
        self.assertEqual(result, {"stale": True})
        self.assertEqual(len(stub.requests), 2)

    def test_corrective_message_names_the_specific_validation_error(self):
        with StubLLMServer() as stub:
            stub.responses = [
                (200, completion(json.dumps({"stale": "not-a-bool"}))),
                (200, completion(json.dumps({"stale": True}))),
            ]
            client_for(stub).complete_json(
                "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
            )
            second_request_messages = stub.requests[1]["body"]["messages"]
        correction = second_request_messages[-1]
        self.assertEqual(correction["role"], "user")
        self.assertIn("'stale' must be a boolean", correction["content"])
        self.assertIn("ONLY the JSON", correction["content"])

    def test_conversation_grows_with_the_failed_attempt_and_correction(self):
        with StubLLMServer() as stub:
            stub.responses = [
                (200, completion("prose, not json")),
                (200, completion(json.dumps({"stale": True}))),
            ]
            client_for(stub).complete_json(
                "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
            )
            second_request_messages = stub.requests[1]["body"]["messages"]
        self.assertEqual(len(second_request_messages), 4)
        self.assertEqual(second_request_messages[0]["role"], "system")
        self.assertEqual(second_request_messages[1]["role"], "user")
        self.assertEqual(second_request_messages[2], {"role": "assistant", "content": "prose, not json"})
        self.assertEqual(second_request_messages[3]["role"], "user")

    def test_retries_exhausted_raises_llm_response_error_naming_the_label(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, completion("never valid json"))]
            with self.assertRaises(LLMResponseError) as ctx:
                client_for(stub).complete_json(
                    "skill text", "user content", _validate_stale_shape,
                    response_label="drift verdict", max_correction_attempts=1,
                )
        self.assertEqual(len(stub.requests), 2)  # initial + 1 correction attempt
        self.assertIn("drift verdict", str(ctx.exception))
        self.assertIn("2 attempt(s)", str(ctx.exception))

    def test_environment_correction_retry_budget_is_used(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, completion("never valid json"))]
            client = LLMClient.from_env(env={
                ENDPOINT_VAR: stub.endpoint, API_KEY_VAR: "test-key", MAX_CORRECTION_ATTEMPTS_VAR: "0",
            }, sleep=lambda seconds: None)
            with self.assertRaises(LLMResponseError):
                client.complete_json(
                    "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
                )
        self.assertEqual(len(stub.requests), 1)

    def test_expected_shape_named_in_corrective_message(self):
        def validate_array(parsed):
            if not isinstance(parsed, list):
                raise ValueError("expected a JSON array")

        with StubLLMServer() as stub:
            stub.responses = [
                (200, completion("not an array")),
                (200, completion(json.dumps([]))),
            ]
            client_for(stub).complete_json(
                "skill text", "user content", validate_array, response_label="extraction response",
                expected_shape="array",
            )
            correction = stub.requests[1]["body"]["messages"][-1]["content"]
        self.assertIn("ONLY the JSON array", correction)

    def test_no_response_format_or_other_provider_specific_field_added(self):
        with StubLLMServer() as stub:
            stub.responses = [
                (200, completion("not json")),
                (200, completion(json.dumps({"stale": True}))),
            ]
            client_for(stub).complete_json(
                "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
            )
        for request in stub.requests:
            self.assertEqual(set(request["body"].keys()), {"model", "messages", "temperature"})

    def test_code_fenced_response_still_parses(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, completion('```json\n{"stale": true}\n```'))]
            result = client_for(stub).complete_json(
                "skill text", "user content", _validate_stale_shape, response_label="drift verdict",
            )
        self.assertEqual(result, {"stale": True})
        self.assertEqual(len(stub.requests), 1)


class FakeBedrockRuntime:
    def __init__(self, responses=None):
        self.requests = []
        self.responses = list(responses or [])

    def converse(self, **request):
        self.requests.append(request)
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return {"output": {"message": {"content": [{"text": "ok"}]}}}


class FakeBoto3:
    __version__ = "1.43.51"
    __file__ = "/ci/site-packages/boto3/__init__.py"

    def __init__(self, runtime):
        self.runtime = runtime
        self.client_calls = []

    def client(self, service, region_name, config):
        self.client_calls.append((service, region_name, config))
        return self.runtime


class TestBedrockAdapter(unittest.TestCase):
    def client(self, runtime=None, **kwargs):
        runtime = runtime or FakeBedrockRuntime()
        module = FakeBoto3(runtime)
        client = BedrockLLMClient(
            region="us-east-1",
            model="anthropic.claude-test-v1",
            boto3_module=module,
            client_config_factory=lambda **settings: settings,
            sleep=lambda _: None,
            **kwargs,
        )
        return client, runtime, module

    def test_from_env_selects_bedrock(self):
        client = LLMClient.from_env(
            env={
                PROVIDER_VAR: "bedrock",
                AWS_REGION_VAR: "eu-west-1",
                MODEL_VAR: "provider.model-v1",
            }
        )
        self.assertIsInstance(client, BedrockLLMClient)
        self.assertEqual(client.region, "eu-west-1")

    def test_constructor_does_not_import_the_ci_only_sdk(self):
        import builtins
        from unittest.mock import patch

        original_import = builtins.__import__

        def reject_boto(name, *args, **kwargs):
            if name == "boto3":
                raise AssertionError("boto3 must remain lazy")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=reject_boto):
            BedrockLLMClient(region="us-east-1", model="provider.model-v1")

    def test_injected_runtime_does_not_require_the_sdk(self):
        client = BedrockLLMClient(
            region="us-east-1",
            model="provider.model-v1",
            runtime_client=FakeBedrockRuntime(),
        )
        self.assertEqual(client.chat([{"role": "user", "content": "hello"}]), "ok")

    def test_converse_maps_system_and_conversation_messages(self):
        client, runtime, _ = self.client()
        result = client.chat(
            [
                {"role": "system", "content": "follow the skill"},
                {"role": "user", "content": "review this"},
                {"role": "assistant", "content": "prior response"},
            ],
            temperature=0.2,
        )
        self.assertEqual(result, "ok")
        self.assertEqual(
            runtime.requests[0],
            {
                "modelId": "anthropic.claude-test-v1",
                "system": [{"text": "follow the skill"}],
                "messages": [
                    {"role": "user", "content": [{"text": "review this"}]},
                    {"role": "assistant", "content": [{"text": "prior response"}]},
                ],
                "inferenceConfig": {"temperature": 0.2},
            },
        )

    def test_converse_text_blocks_are_joined(self):
        runtime = FakeBedrockRuntime(
            [{"output": {"message": {"content": [{"text": "one"}, {"text": " two"}]}}}]
        )
        client, _, _ = self.client(runtime)
        self.assertEqual(client.chat([{"role": "user", "content": "hello"}]), "one two")

    def test_preflight_reports_sdk_version_and_import_path(self):
        client, _, module = self.client()
        details = client.preflight()
        self.assertEqual(details["boto3_version"], "1.43.51")
        self.assertEqual(details["boto3_path"], module.__file__)

    def test_preflight_rejects_runtime_without_converse(self):
        module = FakeBoto3(object())
        client = BedrockLLMClient(
            region="us-east-1", model="model", boto3_module=module,
            client_config_factory=lambda **settings: settings,
        )
        with self.assertRaises(LLMConfigurationError) as ctx:
            client.preflight()
        self.assertIn("1.43.51", str(ctx.exception))
        self.assertIn(module.__file__, str(ctx.exception))
        self.assertIn("requirements-bedrock.txt", str(ctx.exception))

    def test_request_timeout_is_applied_to_the_sdk_client(self):
        client, _, module = self.client(timeout=120)
        client.preflight()
        _, _, config = module.client_calls[0]
        self.assertEqual(config["connect_timeout"], 120)
        self.assertEqual(config["read_timeout"], 120)
        self.assertEqual(config["retries"], {"max_attempts": 0})

    def test_non_retryable_provider_error_is_classified(self):
        class AccessDenied(Exception):
            response = {"Error": {"Code": "AccessDeniedException"}}

        client, _, _ = self.client(FakeBedrockRuntime([AccessDenied("denied")]))
        with self.assertRaises(LLMRequestError) as ctx:
            client.chat([{"role": "user", "content": "hello"}])
        self.assertIn("bedrock", str(ctx.exception))
        self.assertIn("AccessDeniedException", str(ctx.exception))

    def test_throttling_is_retried(self):
        class Throttled(Exception):
            response = {"Error": {"Code": "ThrottlingException"}}

        runtime = FakeBedrockRuntime(
            [Throttled("slow down"), {"output": {"message": {"content": [{"text": "ok"}]}}}]
        )
        client, _, _ = self.client(runtime, max_attempts=2)
        self.assertEqual(client.chat([{"role": "user", "content": "hello"}]), "ok")
        self.assertEqual(len(runtime.requests), 2)



class TestSkillLoading(unittest.TestCase):
    def test_frontmatter_is_stripped(self):
        text = "---\nname: x\ndescription: y\n---\n\n# Body\n\ninstructions\n"
        self.assertEqual(strip_frontmatter(text), "# Body\n\ninstructions\n")

    def test_text_without_frontmatter_is_unchanged(self):
        self.assertEqual(strip_frontmatter("# Body\n"), "# Body\n")

    def test_load_skill_from_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / ".agents" / "skills" / "demo-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: demo-skill\n---\n# Do things\n")
            self.assertEqual(load_skill("demo-skill", root=tmp), "# Do things\n")

    def test_missing_skill_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SkillNotFoundError) as ctx:
                load_skill("absent", root=tmp)
        self.assertIn("absent", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
