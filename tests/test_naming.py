"""Name normalization, hint parsing, and CI-side resolution failures."""

import unittest

from panopticon.naming import (
    UnresolvableNameError,
    interface_hints,
    nearest_hint,
    normalize_name,
    parse_hints,
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


if __name__ == "__main__":
    unittest.main()
