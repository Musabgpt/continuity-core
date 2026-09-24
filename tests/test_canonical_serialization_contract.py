import unittest

from continuity import canonical


class CanonicalSerializationContractTests(unittest.TestCase):
    def test_insertion_order_does_not_change_canonical_bytes(self):
        left = {"z": 1, "a": {"β": "✓", "m": [3, 2, 1]}, "b": ["x", "y"]}
        right = {"b": ["x", "y"], "a": {"m": [3, 2, 1], "β": "✓"}, "z": 1}
        self.assertEqual(canonical(left), canonical(right))

    def test_canonical_serialization_is_utf8_compact_and_sorted(self):
        value = {"b": "✓", "a": "é"}
        self.assertEqual(canonical(value), '{"a":"é","b":"✓"}')
        self.assertNotIn(" ", canonical(value))


if __name__ == "__main__":
    unittest.main()
