"""Public installer launcher tests; every GitHub API interaction is stubbed."""

import base64
import contextlib
import importlib.util
import io
import json
import os
import pty
import select
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_PATH = REPO_ROOT / "install.py"
INSTALL_SOURCE = INSTALL_PATH.read_text()


def _load_installer_module():
    spec = importlib.util.spec_from_file_location("panopticon_public_installer", INSTALL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INSTALLER = _load_installer_module()


class ApiResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _json_response(document):
    return ApiResponse(json.dumps(document).encode())


def _contents_response(source):
    return _json_response(
        {
            "encoding": "base64",
            "content": base64.encodebytes(source.encode()).decode(),
        }
    )


def _http_error(request, status=404, body=b"sensitive-response-body"):
    return urllib.error.HTTPError(request.full_url, status, "failure", {}, io.BytesIO(body))


def _run_isolated(env, stdin_text=None):
    with tempfile.TemporaryDirectory() as child_root:
        script = Path(child_root) / "install.py"
        script.write_text(INSTALL_SOURCE)
        return subprocess.run(
            [sys.executable, str(script)],
            cwd=child_root,
            env=env,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=10,
        )


def _drive_tty_reader(reader, value):
    master, slave = pty.openpty()
    tty_path = os.ttyname(slave)
    result = []
    worker = threading.Thread(target=lambda: result.append(reader(tty_path)))
    worker.start()
    prompt = os.read(master, 4096)
    os.write(master, value.encode() + b"\n")
    worker.join(timeout=5)
    readable, _, _ = select.select([master], [], [], 1)
    output = prompt + (os.read(master, 4096) if readable else b"")
    previous_handler = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        os.close(master)
        os.close(slave)
    finally:
        signal.signal(signal.SIGHUP, previous_handler)
    if worker.is_alive():
        raise AssertionError("terminal reader did not finish")
    return result[0], output


class TestLauncherInputs(unittest.TestCase):
    def test_instance_env_takes_precedence(self):
        self.assertEqual(
            INSTALLER.resolve_instance({"PANOPTICON_INSTANCE": " acme/instance "}),
            "acme/instance",
        )

    def test_invalid_instance_is_rejected(self):
        with self.assertRaisesRegex(INSTALLER.LauncherError, "owner/repo"):
            INSTALLER.resolve_instance({"PANOPTICON_INSTANCE": "invalid"})

    def test_piped_stdin_is_not_used_when_no_terminal_exists(self):
        result = _run_isolated(
            {"PATH": "/usr/bin:/bin"}, stdin_text="acme/instance\nsecret-value\n"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PANOPTICON_INSTANCE", result.stderr)
        self.assertNotIn("secret-value", result.stdout + result.stderr)

    def test_instance_prompt_reads_the_terminal(self):
        value, output = _drive_tty_reader(
            lambda tty_path: INSTALLER._read_tty_line("Instance: ", tty_path),
            "acme/instance",
        )
        self.assertEqual(value, "acme/instance")
        self.assertIn(b"Instance: ", output)

    def test_hidden_token_prompt_does_not_echo_the_token(self):
        token = "top-secret-token"
        value, output = _drive_tty_reader(INSTALLER._read_hidden_token, token)
        self.assertEqual(value, token)
        self.assertIn(b"input hidden", output)
        self.assertNotIn(token.encode(), output)


class TestAuthentication(unittest.TestCase):
    def test_gh_token_precedes_github_token_and_cli(self):
        run = mock.Mock()
        token = INSTALLER.resolve_token(
            {"GH_TOKEN": "first", "GITHUB_TOKEN": "second"},
            which=lambda _name: "/usr/bin/gh",
            run=run,
        )
        self.assertEqual(token, "first")
        run.assert_not_called()

    def test_github_token_is_used_without_gh_token(self):
        self.assertEqual(
            INSTALLER.resolve_token({"GITHUB_TOKEN": "second"}, which=lambda _name: None),
            "second",
        )

    def test_github_cli_token_is_the_final_existing_auth_fallback(self):
        result = mock.Mock(returncode=0, stdout="cli-token\n")
        run = mock.Mock(return_value=result)
        self.assertEqual(
            INSTALLER.resolve_token({}, which=lambda _name: "/usr/bin/gh", run=run),
            "cli-token",
        )
        run.assert_called_once_with(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        )

    def test_anonymous_failure_retries_with_hidden_token(self):
        requests = []

        def urlopen(request, timeout=30):
            requests.append(request)
            if "Authorization" not in request.headers:
                raise _http_error(request)
            if "/contents/install.py" in request.full_url:
                return _contents_response("print('CUSTOM_INSTALLER_RAN')")
            return _json_response({"default_branch": "trunk"})

        output = io.StringIO()
        env = {"PANOPTICON_INSTANCE": "acme/private"}
        with mock.patch.object(INSTALLER, "_read_hidden_token", return_value="prompted-secret"):
            with mock.patch.dict(os.environ, env, clear=True):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(INSTALLER.launch(os.environ, urlopen), 0)

        text = output.getvalue()
        self.assertIn("CUSTOM_INSTALLER_RAN", text)
        self.assertNotIn("prompted-secret", text)
        self.assertEqual(os.environ.get("GH_TOKEN"), None)
        authenticated = [request for request in requests if "Authorization" in request.headers]
        self.assertTrue(authenticated)
        self.assertTrue(
            all(request.headers["Authorization"] == "Bearer prompted-secret" for request in authenticated)
        )

    def test_authenticated_failure_is_controlled_and_redacted(self):
        def urlopen(request, timeout=30):
            raise _http_error(request, status=403)

        with self.assertRaisesRegex(INSTALLER.LauncherError, "token permissions") as caught:
            INSTALLER._fetch_with_authentication(
                "acme/private", {}, "top-secret", urlopen, "/missing-tty"
            )
        self.assertNotIn("top-secret", str(caught.exception))
        self.assertNotIn("sensitive-response-body", str(caught.exception))


class TestInstanceRetrieval(unittest.TestCase):
    def test_explicit_ref_skips_default_branch_lookup(self):
        urlopen = mock.Mock(side_effect=AssertionError("default branch lookup was not expected"))
        self.assertEqual(
            INSTALLER.resolve_ref(
                "acme/instance", {"PANOPTICON_INSTANCE_REF": "release/v2"}, None, urlopen
            ),
            "release/v2",
        )
        urlopen.assert_not_called()

    def test_default_branch_is_resolved_from_repository_metadata(self):
        def urlopen(request, timeout=30):
            self.assertNotIn("Authorization", request.headers)
            return _json_response({"default_branch": "trunk"})

        self.assertEqual(INSTALLER.resolve_ref("acme/public", {}, None, urlopen), "trunk")

    def test_installer_fetch_encodes_ref_and_uses_authorization_header(self):
        seen = []

        def urlopen(request, timeout=30):
            seen.append(request)
            return _contents_response("print('custom')")

        source = INSTALLER.fetch_instance_installer(
            "acme/private", "release/one", "secret-token", urlopen
        )
        self.assertEqual(source, "print('custom')")
        self.assertIn("ref=release%2Fone", seen[0].full_url)
        self.assertNotIn("secret-token", seen[0].full_url)
        self.assertEqual(seen[0].headers["Authorization"], "Bearer secret-token")

    def test_installer_fetch_accepts_github_line_wrapped_base64(self):
        source = "# long installer payload\n" + "print('custom')\n" * 10
        fetched = INSTALLER.fetch_instance_installer(
            "acme/instance",
            "main",
            urlopen=lambda _request, timeout=30: _contents_response(source),
        )
        self.assertEqual(fetched, source)

    def test_custom_payload_receives_marker_working_directory_and_environment(self):
        source = (
            "import os\n"
            "assert __panopticon_instance_payload__ is True\n"
            "print(os.getcwd())\n"
            "print(os.environ['PANOPTICON_SKILLS_LOCATION'])\n"
        )
        with tempfile.TemporaryDirectory() as child_root:
            previous = os.getcwd()
            try:
                os.chdir(child_root)
                with mock.patch.dict(
                    os.environ, {"PANOPTICON_SKILLS_LOCATION": ".custom/skills"}, clear=False
                ):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        INSTALLER.execute_instance_installer(source, "acme/instance", "trunk")
            finally:
                os.chdir(previous)
        self.assertIn(child_root, output.getvalue())
        self.assertIn(".custom/skills", output.getvalue())


class TestDefaultInstancePayload(unittest.TestCase):
    FAKE_INIT = "SCHEMA_VERSION = 1\n"
    FAKE_BOOTSTRAP = (
        "from . import SCHEMA_VERSION\n"
        "def main():\n"
        "    print(f'DEFAULT_BOOTSTRAP_RAN schema={SCHEMA_VERSION}')\n"
        "    return 0\n"
    )

    def test_template_derived_instance_runs_default_bootstrap_without_recursion(self):
        requests = []

        def urlopen(request, timeout=30):
            requests.append(request.full_url)
            if "/contents/panopticon/__init__.py" in request.full_url:
                return _contents_response(self.FAKE_INIT)
            if "/contents/panopticon/bootstrap.py" in request.full_url:
                return _contents_response(self.FAKE_BOOTSTRAP)
            raise AssertionError(f"unexpected URL: {request.full_url}")

        output = io.StringIO()
        env = {
            "PATH": "/usr/bin:/bin",
            "PANOPTICON_INSTANCE": "acme/instance",
            "PANOPTICON_INSTANCE_REF": "trunk",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("urllib.request.urlopen", urlopen):
                with mock.patch.dict(sys.modules, {}, clear=False):
                    with contextlib.redirect_stdout(output):
                        with self.assertRaises(SystemExit) as caught:
                            INSTALLER.execute_instance_installer(
                                INSTALL_SOURCE, "acme/instance", "trunk"
                            )
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("DEFAULT_BOOTSTRAP_RAN schema=1", output.getvalue())
        self.assertEqual(len(requests), 2)

    def test_invalid_or_missing_instance_fails_in_a_real_subprocess(self):
        result = _run_isolated(
            {
                "PATH": "/usr/bin:/bin",
                "PANOPTICON_INSTANCE": "not-a-repository",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner/repo", result.stderr)


if __name__ == "__main__":
    unittest.main()
