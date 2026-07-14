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


if __name__ == "__main__":
    unittest.main()
