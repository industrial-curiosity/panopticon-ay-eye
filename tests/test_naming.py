"""Name normalization, hint parsing, and CI-side resolution failures."""

import unittest

from panopticon.naming import (
    DEPENDENCY_HINT,
    DEPENDENCY_OF_HINT,
    UnresolvableNameError,
    dependency_hints,
    dependency_of_hints,
    interface_hints,
    nearest_hint,
    normalize_name,
    parse_hints,
    resolve_dependency_name,
    resolve_name,
)
from panopticon.candidate_matching import check_candidates, format_report, select_candidates


class TestNormalization(unittest.TestCase):
    def test_rules(self):
        cases = {
            "Orders API": "orders-api",
            "order.events": "order-events",
            "audit_log.events": "audit-log-events",
            "  Billing / Invoices  ": "billing-invoices",
            "kafka:topic:x": "kafka-topic-x",
            "already-canonical": "already-canonical",
            "--Weird---Name--": "weird-name",
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_name(raw), expected, raw)

    def test_hint_wins_over_normalization(self):
        self.assertEqual(resolve_name("Some Raw Title", hint="order-events"), "order-events")

    def test_reviewed_organization_name_overrides_generic_raw_name(self):
        self.assertEqual(resolve_name("events", hint="kafka-order-events"), "kafka-order-events")

    def test_persisted_hint_is_reproducible_without_context(self):
        hint = "orders-api"
        self.assertEqual(resolve_name("implementation_identifier", hint=hint), hint)
        self.assertEqual(resolve_name("different_raw_title", hint=hint), hint)

    def test_unresolvable_name_fails_with_hint_instruction(self):
        with self.assertRaises(UnresolvableNameError) as ctx:
            resolve_name("---", source_files=["config/kafka.properties"])
        message = str(ctx.exception)
        self.assertIn("panopticon-interface", message)
        self.assertIn("config/kafka.properties", message)


class TestHints(unittest.TestCase):
    TEXT = "\n".join(
        [
            "# panopticon-interface order-events",
            "topic=order.events",
            "",
            "// panopticon-interface billing-api  (inline hint)",
            "other=stuff",
            "# panopticon-component payments",
        ]
    )

    def test_parse_hints_finds_all_hint_types(self):
        hints = parse_hints(self.TEXT)
        self.assertIn(("interface", "order-events", 1), hints)
        self.assertIn(("interface", "billing-api", 4), hints)
        self.assertIn(("component", "payments", 6), hints)

    def test_interface_hints_only(self):
        self.assertEqual(interface_hints(self.TEXT), ["order-events", "billing-api"])

    def test_nearest_hint_within_distance(self):
        self.assertEqual(nearest_hint(self.TEXT, 2), "order-events")
        self.assertEqual(nearest_hint(self.TEXT, 5), "billing-api")
        self.assertIsNone(nearest_hint(self.TEXT, 2, max_distance=0))


class TestDependencyHints(unittest.TestCase):
    TEXT = "\n".join(
        [
            "# panopticon-dependency internal-metrics-lib",
            "require github.com/acme/internal-metrics-lib v1.2.3",
            "",
            "// panopticon-dependency-of order-processing-api  (generated client)",
            "implementation com.acme.orders:orders-api-client-sdk:1.0.0",
        ]
    )

    def test_parse_hints_finds_dependency_hint_types(self):
        hints = parse_hints(self.TEXT)
        self.assertIn((DEPENDENCY_HINT, "internal-metrics-lib", 1), hints)
        self.assertIn((DEPENDENCY_OF_HINT, "order-processing-api", 4), hints)

    def test_dependency_hints_only(self):
        self.assertEqual(dependency_hints(self.TEXT), ["internal-metrics-lib"])

    def test_dependency_of_hints_only(self):
        self.assertEqual(dependency_of_hints(self.TEXT), ["order-processing-api"])

    def test_nearest_hint_accepts_dependency_hint_type(self):
        self.assertEqual(
            nearest_hint(self.TEXT, 2, hint_type=DEPENDENCY_HINT), "internal-metrics-lib"
        )
        self.assertIsNone(nearest_hint(self.TEXT, 2, hint_type=DEPENDENCY_OF_HINT))

    def test_nearest_hint_accepts_dependency_of_hint_type(self):
        self.assertEqual(
            nearest_hint(self.TEXT, 5, hint_type=DEPENDENCY_OF_HINT), "order-processing-api"
        )

    def test_no_dependency_hints_present(self):
        self.assertEqual(dependency_hints("no hints here"), [])
        self.assertEqual(dependency_of_hints("no hints here"), [])


class TestResolveDependencyName(unittest.TestCase):
    def test_raw_name_used_verbatim_no_normalization(self):
        # Unlike resolve_name, must NOT lowercase or dash-ify — it's a machine identifier.
        self.assertEqual(resolve_dependency_name("github.com/Acme/Shared-Lib"), "github.com/Acme/Shared-Lib")

    def test_hint_wins_and_is_also_used_verbatim(self):
        self.assertEqual(
            resolve_dependency_name("github.com/acme/shared-lib", hint="Custom_Name"), "Custom_Name"
        )

    def test_whitespace_trimmed(self):
        self.assertEqual(resolve_dependency_name("  github.com/acme/shared-lib  "), "github.com/acme/shared-lib")

    def test_unresolvable_name_fails_with_dependency_hint_instruction(self):
        with self.assertRaises(UnresolvableNameError) as ctx:
            resolve_dependency_name("   ", source_files=["go.mod"])
        message = str(ctx.exception)
        self.assertIn("panopticon-dependency", message)
        self.assertNotIn("panopticon-dependency-of", message)
        self.assertIn("go.mod", message)


class TestCandidateMatching(unittest.TestCase):
    class FakeClient:
        def __init__(self, verdict):
            self.verdict = verdict
            self.user_content = None

        def complete_json(self, _skill, user_content, validator, response_label=None):
            self.user_content = user_content
            validator(self.verdict)
            return self.verdict

    def test_selection_is_bounded_and_same_type(self):
        local = {
            "interfaces": {
                "orders-api": [{"type": "rest"}],
                "payments-api": [{"type": "grpc"}],
            }
        }
        compiled = {
            "interfaces": {
                "orders-api": [{"type": "rest", "owner": None}],
                "orders-service": [{"type": "rest", "owner": None}],
                "payments-api": [{"type": "rest", "owner": None}],
            }
        }
        candidates = select_candidates(local, compiled, max_candidates=1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["instance_name"], "orders-api")
        self.assertEqual(candidates[0]["type"], "rest")

    def test_report_prominently_surfaces_possible_match(self):
        report = format_report({
            "summary": "Review the shared contract.",
            "matches": [{
                "child_name": "events",
                "instance_name": "kafka-order-events",
                "type": "kafka",
                "classification": "likely-same",
                "evidence": "same topic configuration",
            }],
        })
        self.assertIn("review potential organization matches", report)
        self.assertIn("kafka-order-events", report)
        self.assertIn("advisory context", report)

    def test_llm_comparison_is_structured_and_does_not_mutate_indexes(self):
        local = {"interfaces": {"events": [{"type": "kafka"}]}}
        compiled = {"interfaces": {"kafka-order-events": [{"type": "kafka"}]}}
        verdict = {
            "summary": "same topic evidence",
            "matches": [{
                "child_name": "events",
                "instance_name": "kafka-order-events",
                "type": "kafka",
                "classification": "likely-same",
                "evidence": "same topic",
            }],
        }
        client = self.FakeClient(verdict)
        self.assertEqual(check_candidates(local, compiled, client), verdict)
        self.assertIn("kafka-order-events", client.user_content)
        self.assertEqual(local, {"interfaces": {"events": [{"type": "kafka"}]}})
        self.assertEqual(compiled, {"interfaces": {"kafka-order-events": [{"type": "kafka"}]}})


if __name__ == "__main__":
    unittest.main()
