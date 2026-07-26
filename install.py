#!/usr/bin/env python3
"""Launch the installer owned by a Panopticon instance repository.

Run from inside the child repository to initialize:

    curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | python3

Set ``PANOPTICON_INSTANCE=owner/repo`` to skip the instance prompt. Private instances use
``GH_TOKEN``, ``GITHUB_TOKEN``, an existing ``gh auth`` session, or a hidden terminal prompt.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import termios
import time
import types
import urllib.error
import urllib.parse
import urllib.request


API_ROOT = "https://api.github.com"
PAYLOAD_MARKER = "__panopticon_instance_payload__"
TOKEN_ENV_KEYS = ("GH_TOKEN", "GITHUB_TOKEN")


class LauncherError(RuntimeError):
    """A safe, user-facing launcher failure."""


class GitHubRequestError(LauncherError):
    """A GitHub API failure whose response body must not reach diagnostics."""

    def __init__(self, status, operation):
        super().__init__(f"GitHub API returned HTTP {status} while {operation}")
        self.status = status


def _headers(token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "panopticon-installer",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _rate_limit_delay(status, headers, body, now, fallback):
    """Return a GitHub-directed retry delay, or None for a non-rate-limit response."""
    headers = headers or {}
    retry_after = headers.get("Retry-After")
    remaining = headers.get("X-RateLimit-Remaining")
    reset = headers.get("X-RateLimit-Reset")
    identified = (
        status == 429
        or retry_after is not None
        or str(remaining).strip() == "0"
        or "rate limit" in body.lower()
    )
    if status != 429 and (status != 403 or not identified):
        return None
    if retry_after is not None:
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            pass
    if reset is not None:
        try:
            return max(0.0, float(reset) - now())
        except (TypeError, ValueError):
            pass
    return fallback


def _api_json(url, token=None, urlopen=urllib.request.urlopen, max_attempts=3, sleep=time.sleep,
              now=time.time, print_fn=print):
    request = urllib.request.Request(url, headers=_headers(token))
    last_error = None
    for attempt in range(1, max_attempts + 1):
        rate_limited = False
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            headers = exc.headers
            with exc:
                body = exc.read().decode("utf-8", "replace")[:400]
            last_error = GitHubRequestError(exc.code, "accessing the instance repository")
            fallback = 2 ** (attempt - 1)
            delay = _rate_limit_delay(exc.code, headers, body, now, fallback)
            if delay is None:
                raise last_error from None
            rate_limited = True
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = LauncherError(f"could not access the GitHub API: {type(exc).__name__}")
            delay = 2 ** (attempt - 1)
        except json.JSONDecodeError as exc:
            raise LauncherError(f"could not access the GitHub API: {type(exc).__name__}") from None
        if attempt < max_attempts:
            if rate_limited:
                print_fn(
                    "Panopticon installer: GitHub API rate limited; "
                    f"retrying in {int(delay + 0.999)} seconds..."
                )
            sleep(delay)
    raise last_error


def _read_tty_line(prompt, tty_path="/dev/tty"):
    try:
        descriptor = os.open(tty_path, os.O_RDWR)
    except OSError:
        return None
    value = bytearray()
    try:
        os.write(descriptor, prompt.encode())
        while True:
            character = os.read(descriptor, 1)
            if not character or character in (b"\n", b"\r"):
                break
            value.extend(character)
    finally:
        os.close(descriptor)
    return value.decode("utf-8").strip()


def _read_hidden_token(tty_path="/dev/tty"):
    try:
        descriptor = os.open(tty_path, os.O_RDWR)
        previous = termios.tcgetattr(descriptor)
    except (OSError, termios.error):
        return None
    hidden = previous.copy()
    hidden[3] &= ~termios.ECHO
    token = bytearray()
    try:
        termios.tcsetattr(descriptor, termios.TCSANOW, hidden)
        os.write(descriptor, b"GitHub token for the private instance (input hidden): ")
        while True:
            character = os.read(descriptor, 1)
            if not character or character in (b"\n", b"\r"):
                break
            token.extend(character)
        os.write(descriptor, b"\n")
    finally:
        termios.tcsetattr(descriptor, termios.TCSANOW, previous)
        os.close(descriptor)
    return token.decode("utf-8").strip()


def _validate_instance(value):
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise LauncherError(f"PANOPTICON_INSTANCE must be 'owner/repo', got: {value!r}")
    return parts


def resolve_instance(env=None, tty_path="/dev/tty"):
    env = env if env is not None else os.environ
    value = env.get("PANOPTICON_INSTANCE", "").strip()
    if not value:
        value = _read_tty_line(
            "Panopticon instance (owner/repo, or set PANOPTICON_INSTANCE): ", tty_path
        )
    if not value:
        raise LauncherError(
            "PANOPTICON_INSTANCE is required in non-interactive runs.\n"
            "Run this exact command from inside the child clone:\n\n"
            "    curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/"
            "panopticon-ay-eye/main/install.py | "
            "PANOPTICON_INSTANCE='owner/panopticon-instance' python3"
        )
    _validate_instance(value)
    return value


def resolve_token(env=None, which=shutil.which, run=subprocess.run):
    env = env if env is not None else os.environ
    for key in TOKEN_ENV_KEYS:
        if env.get(key):
            return env[key].strip()
    if which("gh"):
        try:
            result = run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return None


def _repo_url(instance):
    owner, repo = _validate_instance(instance)
    return f"{API_ROOT}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"


def resolve_ref(instance, env=None, token=None, urlopen=urllib.request.urlopen):
    env = env if env is not None else os.environ
    explicit_ref = env.get("PANOPTICON_INSTANCE_REF", "").strip()
    if explicit_ref:
        return explicit_ref
    metadata = _api_json(_repo_url(instance), token, urlopen)
    default_branch = metadata.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch.strip():
        raise LauncherError(f"GitHub returned no default branch for {instance}")
    return default_branch


def fetch_instance_installer(instance, ref, token=None, urlopen=urllib.request.urlopen):
    url = f"{_repo_url(instance)}/contents/install.py?{urllib.parse.urlencode({'ref': ref})}"
    document = _api_json(url, token, urlopen)
    if document.get("encoding") != "base64" or not isinstance(document.get("content"), str):
        raise LauncherError(f"GitHub returned an invalid install.py response for {instance} at {ref}")
    try:
        encoded_content = "".join(document["content"].split())
        return base64.b64decode(encoded_content, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise LauncherError(f"GitHub returned an invalid install.py payload for {instance} at {ref}") from exc


def _fetch_payload(instance, env, token, urlopen):
    ref = resolve_ref(instance, env, token, urlopen)
    return ref, fetch_instance_installer(instance, ref, token, urlopen)


def _fetch_with_authentication(instance, env, token, urlopen, tty_path):
    try:
        return token, _fetch_payload(instance, env, token, urlopen)
    except GitHubRequestError as exc:
        if token:
            raise LauncherError(
                f"cannot access {instance} (HTTP {exc.status}). Check the repository name, token "
                "permissions, and PANOPTICON_INSTANCE_REF"
            ) from None

    prompted_token = _read_hidden_token(tty_path)
    if not prompted_token:
        raise LauncherError(
            f"cannot access {instance}. Check the repository name or provide authentication with "
            "GH_TOKEN or GITHUB_TOKEN in non-interactive runs"
        )
    try:
        return prompted_token, _fetch_payload(instance, env, prompted_token, urlopen)
    except GitHubRequestError as exc:
        raise LauncherError(
            f"cannot access {instance} after authentication (HTTP {exc.status}). Check the "
            "repository name, token permissions, and PANOPTICON_INSTANCE_REF"
        ) from None


def execute_instance_installer(source, instance, ref):
    globals_map = {
        "__name__": "__main__",
        "__file__": f"github://{instance}/install.py@{ref}",
        "__package__": None,
        PAYLOAD_MARKER: True,
    }
    exec(compile(source, globals_map["__file__"], "exec"), globals_map)


def launch(env=None, urlopen=urllib.request.urlopen, tty_path="/dev/tty"):
    env = env if env is not None else os.environ
    instance = resolve_instance(env, tty_path)
    token = resolve_token(env)
    token, (ref, source) = _fetch_with_authentication(
        instance, env, token, urlopen, tty_path
    )

    env["PANOPTICON_INSTANCE"] = instance
    env["PANOPTICON_INSTANCE_REF"] = ref
    if token and not env.get("GH_TOKEN") and not env.get("GITHUB_TOKEN"):
        env["GH_TOKEN"] = token

    print(f"Panopticon instance installer: {instance}@{ref}")
    execute_instance_installer(source, instance, ref)
    return 0


def _load_default_payload_from_github(instance, ref=None):
    """Load the default instance bootstrap when this template file is the fetched payload."""
    owner, repo = _validate_instance(instance)
    token = resolve_token()
    ref = ref or os.environ.get("PANOPTICON_INSTANCE_REF", "").strip() or "main"

    def fetch(path):
        url = (
            f"{API_ROOT}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
            f"/contents/{path}?{urllib.parse.urlencode({'ref': ref})}"
        )
        document = _api_json(url, token)
        try:
            if document.get("encoding") != "base64" or not isinstance(
                document.get("content"), str
            ):
                raise KeyError("encoding")
            encoded_content = "".join(document["content"].split())
            return base64.b64decode(encoded_content, validate=True).decode("utf-8")
        except (KeyError, ValueError, UnicodeDecodeError) as exc:
            raise LauncherError(
                f"GitHub returned an invalid {path} payload for {instance} at {ref}"
            ) from exc

    package = types.ModuleType("panopticon")
    package.__path__ = []
    package.__package__ = "panopticon"
    exec(
        compile(fetch("panopticon/__init__.py"), "panopticon/__init__.py", "exec"),
        package.__dict__,
    )
    sys.modules["panopticon"] = package

    recovery = types.ModuleType("panopticon.recovery")
    recovery.__package__ = "panopticon"
    package.recovery = recovery
    sys.modules["panopticon.recovery"] = recovery
    exec(
        compile(fetch("panopticon/recovery.py"), "panopticon/recovery.py", "exec"),
        recovery.__dict__,
    )

    providers = types.ModuleType("panopticon.providers")
    providers.__package__ = "panopticon"
    package.providers = providers
    sys.modules["panopticon.providers"] = providers
    exec(
        compile(fetch("panopticon/providers.py"), "panopticon/providers.py", "exec"),
        providers.__dict__,
    )

    callers = types.ModuleType("panopticon.callers")
    callers.__package__ = "panopticon"
    package.callers = callers
    sys.modules["panopticon.callers"] = callers
    exec(
        compile(fetch("panopticon/callers.py"), "panopticon/callers.py", "exec"),
        callers.__dict__,
    )

    bootstrap = types.ModuleType("panopticon.bootstrap")
    bootstrap.__package__ = "panopticon"
    package.bootstrap = bootstrap
    sys.modules["panopticon.bootstrap"] = bootstrap
    exec(
        compile(fetch("panopticon/bootstrap.py"), "panopticon/bootstrap.py", "exec"),
        bootstrap.__dict__,
    )
    return bootstrap.main


def run_instance_payload():
    instance = os.environ.get("PANOPTICON_INSTANCE", "").strip()
    if not instance:
        raise LauncherError("launcher did not provide PANOPTICON_INSTANCE to the instance payload")
    main = _load_default_payload_from_github(instance)
    return main() or 0


def main():
    try:
        if globals().get(PAYLOAD_MARKER):
            return run_instance_payload()
        return launch()
    except LauncherError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
