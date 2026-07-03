"""Agent runtime: request shape, retries, and fail-loudly degradation paths, via a stub server."""

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from panopticon.llm import (
    API_KEY_VAR,
    ENDPOINT_VAR,
    LLMClient,
    LLMRequestError,
    LLMResponseError,
    MissingRequirementError,
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
        message = str(ctx.exception)
        self.assertNotIn(ENDPOINT_VAR + " ", message.split(":")[1])
        self.assertIn(API_KEY_VAR, message)
        self.assertIn("PANOPTICON_INSTANCE_TOKEN", message)

    def test_malformed_response_is_a_loud_error(self):
        with StubLLMServer() as stub:
            stub.responses = [(200, {"unexpected": True})]
            with self.assertRaises(LLMResponseError):
                client_for(stub).chat([{"role": "user", "content": "hi"}])


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
