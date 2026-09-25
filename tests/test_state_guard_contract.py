import copy
import unittest

from continuity_state_guard import validate_state_payload


class StateGuardContractTests(unittest.TestCase):
    def valid_state(self):
        return {
            "schema_version": 2,
            "project": "Demo",
            "goal": "Continuity",
            "status": "active",
            "constraints": [],
            "decisions": [],
            "next_action": None,
            "updated_at": "2026-09-25T00:00:00Z",
            "revision": 0,
        }

    def test_valid_payload_is_accepted_without_mutation(self):
        state = self.valid_state()
        before = copy.deepcopy(state)
        self.assertIsNone(validate_state_payload(state))
        self.assertEqual(state, before)

    def test_invalid_revision_has_stable_diagnostic(self):
        state = self.valid_state()
        state["revision"] = -1
        first = second = None
        for _ in range(2):
            try:
                validate_state_payload(state)
            except ValueError as exc:
                if first is None:
                    first = str(exc)
                else:
                    second = str(exc)
        self.assertEqual(first, "Transaction state invalid: schema v2 requires non-negative integer revision.")
        self.assertEqual(first, second)

    def test_missing_field_is_first_diagnostic(self):
        state = self.valid_state()
        del state["goal"]
        with self.assertRaisesRegex(ValueError, r"^Transaction state invalid: missing field goal\.$"):
            validate_state_payload(state)

    def test_bool_revision_is_rejected(self):
        state = self.valid_state()
        state["revision"] = True
        with self.assertRaisesRegex(ValueError, r"^Transaction state invalid: schema v2 requires non-negative integer revision\.$"):
            validate_state_payload(state)

    def test_schema_v1_remains_valid_without_revision(self):
        state = self.valid_state()
        state["schema_version"] = 1
        del state["revision"]
        self.assertIsNone(validate_state_payload(state))


if __name__ == "__main__":
    unittest.main()
