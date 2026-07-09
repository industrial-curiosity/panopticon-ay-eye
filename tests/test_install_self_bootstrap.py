"""install.py's self-bootstrapping path: piped-curl fallback when the panopticon package isn't
importable locally.

These tests run install.py in real, isolated subprocesses rather than importing it in-process.
install.py mutates sys.modules at module scope (installing fake `panopticon`/`panopticon.bootstrap`
entries) and its self-bootstrap branch only triggers when `panopticon` genuinely isn't importable —
neither of those is safe or even reproducible inside this shared test process, which already has the
real `panopticon` package imported.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_PY_SOURCE = (REPO_ROOT / "install.py").read_text()


def _isolated_install_py(child_root):
    """Copy install.py into `child_root`, which has no sibling panopticon/ package, so
    `from panopticon.bootstrap import main` genuinely fails there."""
    script = Path(child_root) / "install.py"
    script.write_text(INSTALL_PY_SOURCE)
    return script


def _run(args, child_root, env, stdin_text=None, timeout=15):
    return subprocess.run(
        args,
        cwd=child_root,
        env=env,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestModuleNotFoundExit(unittest.TestCase):
    """The top-level `except ModuleNotFoundError` block when PANOPTICON_INSTANCE is unset."""

    def test_exits_clearly_when_non_interactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = _isolated_install_py(tmp)
            result = _run(
                [sys.executable, str(script)],
                tmp,
                env={"PATH": "/usr/bin:/bin"},
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PANOPTICON_INSTANCE", result.stderr)
        self.assertIn("export PANOPTICON_INSTANCE=", result.stderr)
        self.assertIn("curl -fsSL", result.stderr)

    def test_still_exits_when_piped_stdin_has_content(self):
        # subprocess stdin here is a pipe carrying real bytes, not a terminal — matching the
        # actual `curl ... | python3` shape, where stdin is "readable" but isatty() is false.
        # Confirms the script doesn't mistake available piped bytes for an interactive prompt.
        with tempfile.TemporaryDirectory() as tmp:
            script = _isolated_install_py(tmp)
            result = _run(
                [sys.executable, str(script)],
                tmp,
                env={"PATH": "/usr/bin:/bin"},
                stdin_text="acme/panopticon-instance\n",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PANOPTICON_INSTANCE", result.stderr)


class TestLoadFromGithubSelfBootstrap(unittest.TestCase):
    """`_load_from_github` fetches panopticon/__init__.py and panopticon/bootstrap.py from the
    instance repo and installs them into sys.modules so the retry import succeeds — verified
    end-to-end: a stubbed GitHub API serves fake package files, and the real install.py module
    body runs to completion, proving the installed modules are usable (relative imports resolve,
    `main` is callable)."""

    FAKE_INIT_PY = "SCHEMA_VERSION = 1\n"
    FAKE_BOOTSTRAP_PY = (
        "from . import SCHEMA_VERSION\n"
        "def main():\n"
        "    print(f'FAKE_BOOTSTRAP_RAN schema={SCHEMA_VERSION}')\n"
        "    return 0\n"
    )

    def _wrapper_source(self, install_py_path):
        return f'''
import base64, json, sys
from io import BytesIO
from unittest.mock import patch

FAKE_FILES = {{
    "panopticon/__init__.py": {self.FAKE_INIT_PY!r},
    "panopticon/bootstrap.py": {self.FAKE_BOOTSTRAP_PY!r},
}}

def fake_urlopen(request, timeout=30):
    url = request.full_url
    for path, content in FAKE_FILES.items():
        if f"/contents/{{path}}" in url:
            body = {{"encoding": "base64", "content": base64.b64encode(content.encode()).decode()}}
            return BytesIO(json.dumps(body).encode())
    raise AssertionError(f"unexpected url in self-bootstrap test: {{url}}")

with patch("urllib.request.urlopen", fake_urlopen):
    with open({str(install_py_path)!r}) as f:
        source = f.read()
    g = {{"__name__": "__main__", "__file__": {str(install_py_path)!r}}}
    exec(compile(source, {str(install_py_path)!r}, "exec"), g)
'''

    def test_downloads_and_installs_modules_then_runs_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = _isolated_install_py(tmp)
            wrapper = Path(tmp) / "wrapper.py"
            wrapper.write_text(self._wrapper_source(script))
            result = _run(
                [sys.executable, str(wrapper)],
                tmp,
                env={"PATH": "/usr/bin:/bin", "PANOPTICON_INSTANCE": "acme/panopticon-instance"},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FAKE_BOOTSTRAP_RAN schema=1", result.stdout)

    def test_http_error_exits_with_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = _isolated_install_py(tmp)
            wrapper_source = f'''
import sys
from unittest.mock import patch
import urllib.error

def fake_urlopen(request, timeout=30):
    raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {{}}, None)

with patch("urllib.request.urlopen", fake_urlopen):
    with open({str(script)!r}) as f:
        source = f.read()
    g = {{"__name__": "__main__", "__file__": {str(script)!r}}}
    exec(compile(source, {str(script)!r}, "exec"), g)
'''
            wrapper = Path(tmp) / "wrapper.py"
            wrapper.write_text(wrapper_source)
            result = _run(
                [sys.executable, str(wrapper)],
                tmp,
                env={"PATH": "/usr/bin:/bin", "PANOPTICON_INSTANCE": "acme/panopticon-instance"},
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GitHub API 404", result.stderr)
        self.assertIn("panopticon/__init__.py", result.stderr)


if __name__ == "__main__":
    unittest.main()
