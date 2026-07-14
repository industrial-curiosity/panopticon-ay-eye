"""Dependency-indexing capability: registry-host detection and instance cross-reference.

Mirrors org_diagram_link.py's live-lookup test style: config/checkout consulted first with no
network call, live fallback only when no checkout is usable, and never a guess on failure.
"""

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

from panopticon.dependencies import dumps_index, empty_index
from panopticon.dependency_lookup import is_internal_registry, lookup_registered_producer


def _urlopen_no_call_expected(request, timeout=30):
    raise AssertionError(f"unexpected network call: {request.full_url}")


def _make_contents_urlopen(doc=None, fail=False):
    def urlopen(request, timeout=30):
        if fail:
            raise HTTPError(request.full_url, 404, "Not Found", {}, BytesIO(b"{}"))
        import base64

        content = base64.b64encode(dumps_index(doc).encode()).decode()
        return BytesIO(json.dumps({"content": content, "encoding": "base64"}).encode())

    return urlopen


def _write_compiled_index(instance_root, doc):
    path = Path(instance_root) / "dependencies" / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_index(doc), encoding="utf-8")


def _doc_with_owner(name, owner_repo="acme-shared-lib"):
    doc = empty_index("compiled")
    doc["dependencies"][name] = [
        {
            "owner": {"repo": owner_repo, "component": None},
            "ecosystem": "go",
            "producer": [{"repo": owner_repo, "source_files": ["go.mod"]}],
            "consumer": [],
        }
    ]
    return doc


class TestIsInternalRegistry(unittest.TestCase):
    def test_bare_host_match(self):
        self.assertTrue(is_internal_registry("packages.example.com", ["packages.example.com"]))

    def test_url_with_scheme_and_path_match(self):
        self.assertTrue(
            is_internal_registry(
                "https://packages.example.com/api/pypi/pypi-local", ["packages.example.com"]
            )
        )

    def test_no_match(self):
        self.assertFalse(is_internal_registry("pypi.org", ["packages.example.com"]))

    def test_empty_registries_never_matches(self):
        self.assertFalse(is_internal_registry("packages.example.com", []))

    def test_empty_url_never_matches(self):
        self.assertFalse(is_internal_registry("", ["packages.example.com"]))
        self.assertFalse(is_internal_registry(None, ["packages.example.com"]))


class TestLookupRegisteredProducer(unittest.TestCase):
    def test_checkout_hit_with_no_network_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_compiled_index(tmp, _doc_with_owner("github.com/acme/shared-lib"))
            owner = lookup_registered_producer(
                "github.com/acme/shared-lib", instance_root=tmp, urlopen=_urlopen_no_call_expected
            )
        self.assertEqual(owner, {"repo": "acme-shared-lib", "component": None})

    def test_checkout_present_but_name_absent_does_not_fall_back_to_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_compiled_index(tmp, _doc_with_owner("github.com/acme/shared-lib"))
            owner = lookup_registered_producer(
                "github.com/acme/other-lib",
                instance="acme/panopticon-instance",
                instance_root=tmp,
                urlopen=_urlopen_no_call_expected,
            )
        self.assertIsNone(owner)

    def test_no_checkout_falls_back_to_live_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = lookup_registered_producer(
                "github.com/acme/shared-lib",
                instance="acme/panopticon-instance",
                instance_root=tmp,
                env={"GH_TOKEN": "tok"},
                urlopen=_make_contents_urlopen(_doc_with_owner("github.com/acme/shared-lib")),
            )
        self.assertEqual(owner, {"repo": "acme-shared-lib", "component": None})

    def test_no_instance_root_uses_live_api_directly(self):
        owner = lookup_registered_producer(
            "github.com/acme/shared-lib",
            instance="acme/panopticon-instance",
            env={"GH_TOKEN": "tok"},
            urlopen=_make_contents_urlopen(_doc_with_owner("github.com/acme/shared-lib")),
        )
        self.assertEqual(owner, {"repo": "acme-shared-lib", "component": None})

    def test_live_api_failure_returns_none_not_a_guess(self):
        owner = lookup_registered_producer(
            "github.com/acme/shared-lib",
            instance="acme/panopticon-instance",
            env={},
            urlopen=_make_contents_urlopen(fail=True),
        )
        self.assertIsNone(owner)

    def test_no_instance_root_and_no_instance_returns_none_with_no_network_attempt(self):
        owner = lookup_registered_producer("github.com/acme/shared-lib", env={})
        self.assertIsNone(owner)


if __name__ == "__main__":
    unittest.main()
