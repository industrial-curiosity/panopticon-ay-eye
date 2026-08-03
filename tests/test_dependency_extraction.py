"""Dependency extraction driver: parser folding, interface-link resolution, LLM fallback tagging,
registry-host/instance-cross-reference layers, parser-gap recommendations."""

import json
import tempfile
import unittest
from pathlib import Path

from panopticon.dependencies import KIND_LOCAL, validate_index
from panopticon.dependency_extraction import (
    dependency_candidates_to_index,
    detecting_dependency_parsers,
    extract_repo,
    fallback_candidate_files,
    llm_extract,
    parser_gap_recommendations,
    resolve_candidate_internality,
    run_dependency_parsers,
)
from panopticon.index import save_index as save_interface_index
from panopticon.index import empty_index as empty_interface_index
from panopticon.llm import LLMResponseError
from panopticon.naming import UnresolvableNameError

from .test_extraction import FakeClient

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_GO_REPO = FIXTURES / "sample_go_repo"
SAMPLE_REPO = FIXTURES / "sample_repo"  # has no go.mod — used as a "no dependency parser" fixture
REPO_ROOT = Path(__file__).resolve().parent.parent


class TestDetectingDependencyParsers(unittest.TestCase):
    def test_go_repo_detects_go_parser(self):
        self.assertEqual(list(detecting_dependency_parsers(SAMPLE_GO_REPO)), ["go"])

    def test_non_go_repo_detects_nothing(self):
        self.assertEqual(detecting_dependency_parsers(SAMPLE_REPO), {})

    def test_run_dependency_parsers_groups_by_ecosystem(self):
        results = run_dependency_parsers(SAMPLE_GO_REPO)
        self.assertEqual(list(results), ["go"])
        self.assertTrue(results["go"])


class TestDependencyCandidatesToIndex(unittest.TestCase):
    def test_full_extraction_over_sample_go_repo(self):
        doc, summary = extract_repo(SAMPLE_GO_REPO, "svc-b")
        validate_index(doc, kind=KIND_LOCAL, repo="svc-b")
        self.assertEqual(summary, [])

        (producer_entry,) = doc["dependencies"]["github.com/acme/svc-b"]
        self.assertEqual(producer_entry["ecosystem"], "go")
        self.assertEqual(producer_entry["owner"], {"repo": "svc-b", "component": None})
        self.assertEqual(producer_entry["producer"][0]["source_files"], ["go.mod"])

        (consumer_entry,) = doc["dependencies"]["github.com/acme/shared-lib"]
        self.assertIsNone(consumer_entry["owner"])
        consumer_robj = consumer_entry["consumer"][0]
        self.assertEqual(consumer_robj["source_files"], ["go.mod", "main.go"])
        self.assertEqual(
            consumer_robj["apis"],
            ["github.com/acme/shared-lib/client", "github.com/acme/shared-lib/metrics"],
        )

    def test_unresolvable_name_fails_with_dependency_hint_instruction(self):
        candidates = [
            {
                "raw_name": "   ",
                "hint": None,
                "ecosystem": "go",
                "role": "consumer",
                "source_file": "go.mod",
                "owned": False,
                "component": None,
                "apis": None,
                "links_to_interface_hint": None,
            }
        ]
        with self.assertRaises(UnresolvableNameError) as ctx:
            dependency_candidates_to_index(candidates, "svc-x")
        self.assertIn("panopticon-dependency", str(ctx.exception))

    def _candidate(self, **overrides):
        base = {
            "raw_name": "github.com/acme/shared-lib",
            "hint": None,
            "ecosystem": "go",
            "role": "consumer",
            "source_file": "go.mod",
            "owned": False,
            "component": None,
            "apis": None,
            "links_to_interface_hint": None,
        }
        base.update(overrides)
        return base

    def test_links_to_interface_resolved_from_local_interface_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            iface_doc = empty_interface_index(kind="local")
            iface_doc["interfaces"]["order-processing-api"] = [
                {
                    "owner": {"repo": "svc-x", "component": "api"},
                    "type": "rest",
                    "consumer": [],
                    "producer": [{"repo": "svc-x", "source_files": ["api/openapi.json"]}],
                }
            ]
            save_interface_index(
                iface_doc, Path(tmp) / "panopticon" / "index.json", kind="local", repo="svc-x"
            )
            candidates = [self._candidate(links_to_interface_hint="order-processing-api")]
            doc = dependency_candidates_to_index(candidates, "svc-x", repo_root=tmp)
        (entry,) = doc["dependencies"]["github.com/acme/shared-lib"]
        self.assertEqual(entry["links_to_interface"], {"name": "order-processing-api", "type": "rest"})

    def test_links_to_interface_hint_unresolvable_locally_is_left_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidates = [self._candidate(links_to_interface_hint="some-other-repos-api")]
            doc = dependency_candidates_to_index(candidates, "svc-x", repo_root=tmp)
        (entry,) = doc["dependencies"]["github.com/acme/shared-lib"]
        self.assertNotIn("links_to_interface", entry)

    def test_no_repo_root_leaves_link_unset(self):
        candidates = [self._candidate(links_to_interface_hint="order-processing-api")]
        doc = dependency_candidates_to_index(candidates, "svc-x")
        (entry,) = doc["dependencies"]["github.com/acme/shared-lib"]
        self.assertNotIn("links_to_interface", entry)


class TestResolveCandidateInternality(unittest.TestCase):
    def test_resolves_via_registry_host(self):
        org_config = {"internal_registries": ["packages.example.com"]}
        self.assertTrue(
            resolve_candidate_internality(
                "acme-shared-lib", "https://packages.example.com/simple/acme-shared-lib",
                org_config,
            )
        )

    def test_resolves_via_instance_cross_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            from panopticon.dependencies import dumps_index, empty_index as empty_dep_index

            doc = empty_dep_index("compiled")
            doc["dependencies"]["acme-shared-lib"] = [
                {
                    "owner": {"repo": "acme-shared-lib", "component": None},
                    "ecosystem": "python",
                    "producer": [{"repo": "acme-shared-lib", "source_files": ["pyproject.toml"]}],
                    "consumer": [],
                }
            ]
            path = Path(tmp) / "dependencies" / "index.json"
            path.parent.mkdir(parents=True)
            path.write_text(dumps_index(doc), encoding="utf-8")
            org_config = {"internal_registries": []}
            self.assertTrue(
                resolve_candidate_internality(
                    "acme-shared-lib", None, org_config, instance_root=tmp
                )
            )

    def test_neither_layer_resolves(self):
        org_config = {"internal_registries": ["packages.example.com"]}
        self.assertFalse(
            resolve_candidate_internality("requests", "https://pypi.org/simple/requests", org_config)
        )


class TestFallbackSelection(unittest.TestCase):
    def test_covered_and_oversized_files_are_excluded(self):
        covered = {"go.mod", "main.go"}
        files = fallback_candidate_files(SAMPLE_GO_REPO, covered)
        self.assertNotIn("go.mod", files)

    def test_ci_mode_restricts_to_changed_files(self):
        files = fallback_candidate_files(SAMPLE_REPO, set(), changed_files=["config/topics.yaml"])
        self.assertEqual(files, ["config/topics.yaml"])


class TestAnalysisScope(unittest.TestCase):
    def write_config(self, root):
        config_dir = root / "panopticon"
        config_dir.mkdir()
        (config_dir / "config.json").write_text(
            '{"schema_version": 1, "repo": "svc", "instance": "acme/panopticon", "docs_location": "docs"}'
        )

    def test_declaration_hint_filters_only_annotated_go_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_config(root)
            (root / "go.mod").write_text(
                "module github.com/acme/svc\n\n# panopticon-ignore declaration\n"
                "require github.com/acme/ignored v1.0.0\nrequire github.com/acme/kept v1.0.0\n"
            )
            doc, summary = extract_repo(root, "svc")
        self.assertIn("github.com/acme/kept", doc["dependencies"])
        self.assertNotIn("github.com/acme/ignored", doc["dependencies"])
        self.assertIn("excluded go.mod:4 (explicit declaration hint)", summary)

    def test_illustrative_fallback_file_is_never_sent_to_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "examples").mkdir()
            (root / "examples" / "package.json").write_text('{"name": "example"}')
            client = FakeClient("[]")
            extract_repo(root, "svc", client=client, changed_files=["examples/package.json"], skill_root=REPO_ROOT)
        self.assertEqual(client.calls, [])

    def test_internal_dependencies_in_samples_and_fixtures_are_neither_indexed_nor_sent_to_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory, package in (("samples", "sample-library"), ("fixtures", "fixture-library")):
                path = root / directory
                path.mkdir()
                (path / "package.json").write_text(
                    f'{{"dependencies": {{"@acme/{package}": "1.0.0"}}}}'
                )
            client = FakeClient('[{"raw_name": "@acme/sample-library", "ecosystem": "npm", '
                                '"source_file": "samples/package.json"}]')
            doc, summary = extract_repo(
                root,
                "svc",
                client=client,
                changed_files=["samples/package.json", "fixtures/package.json"],
                skill_root=REPO_ROOT,
            )
        self.assertEqual(doc["dependencies"], {})
        self.assertEqual(client.calls, [])
        self.assertIn("excluded samples/package.json (illustrative directory: samples)", summary)
        self.assertIn("excluded fixtures/package.json (illustrative directory: fixtures)", summary)


class TestLLMFallback(unittest.TestCase):
    def llm_candidates(self):
        return [
            {
                "raw_name": "acme-shared-auth-lib",
                "hint": None,
                "ecosystem": "python",
                "role": "consumer",
                "owned": False,
                "component": None,
                "source_file": "requirements.txt",
                "apis": ["acme_shared_auth.client"],
                "links_to_interface_hint": None,
            }
        ]

    def test_entries_are_tagged_and_gap_reported(self):
        client = FakeClient(json.dumps(self.llm_candidates()))
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["extracted_by"], "llm")
        doc = dependency_candidates_to_index(candidates, "svc-x")
        entry = doc["dependencies"]["acme-shared-auth-lib"][0]
        self.assertEqual(entry["extracted_by"], "llm")
        self.assertEqual(entry["consumer"][0]["apis"], ["acme_shared_auth.client"])
        (recommendation,) = parser_gap_recommendations(candidates)
        self.assertIn("'python'", recommendation)
        self.assertIn("deterministic parser", recommendation)

    def test_skill_is_loaded_as_system_prompt(self):
        client = FakeClient("[]")
        llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        skill_text, user_content = client.calls[0]
        self.assertIn("Response contract", skill_text)
        self.assertIn("config/topics.yaml", user_content)

    def test_no_candidate_files_makes_no_call(self):
        client = FakeClient("[]")
        self.assertEqual(llm_extract(client, SAMPLE_REPO, [], skill_root=REPO_ROOT), [])
        self.assertEqual(client.calls, [])

    def test_malformed_response_fails_loudly(self):
        client = FakeClient("I found some dependencies!")
        with self.assertRaises(LLMResponseError):
            llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)

    def test_prose_first_response_recovers_on_retry(self):
        client = FakeClient([
            "Looking at these files, I can identify the following dependencies...",
            json.dumps(self.llm_candidates()),
        ])
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["raw_name"], "acme-shared-auth-lib")
        self.assertEqual(len(client.chat_calls), 2)

    def test_item_missing_required_field_recovers_on_retry(self):
        malformed = [{"ecosystem": "python", "source_file": "requirements.txt"}]  # raw_name missing
        client = FakeClient([json.dumps(malformed), json.dumps(self.llm_candidates())])
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["raw_name"], "acme-shared-auth-lib")
        self.assertEqual(len(client.chat_calls), 2)

    def test_item_missing_field_eventually_fails_loudly(self):
        malformed = [{"ecosystem": "python", "source_file": "requirements.txt"}]
        client = FakeClient(json.dumps(malformed))
        with self.assertRaises(LLMResponseError):
            llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)

    def test_code_fenced_response_is_accepted(self):
        client = FakeClient("```json\n" + json.dumps(self.llm_candidates()) + "\n```")
        candidates = llm_extract(client, SAMPLE_REPO, ["config/topics.yaml"], skill_root=REPO_ROOT)
        self.assertEqual(candidates[0]["raw_name"], "acme-shared-auth-lib")


if __name__ == "__main__":
    unittest.main()
