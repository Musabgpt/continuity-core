import json
import tempfile
import unittest
from pathlib import Path

import continuity


class EventChainCanonicalContractTests(unittest.TestCase):
    def test_chain_hash_is_based_on_canonical_event_bytes(self):
        original_root = continuity.ROOT
        try:
            rows = [
                {"type": "success", "message": "ok", "ts": "2026-01-01T00:00:00Z"},
                {"ts": "2026-01-01T00:00:00Z", "message": "ok", "type": "success"},
            ]
            hashes = []
            for row in rows:
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    (root / "continuity").mkdir()
                    continuity.configure_root(root)
                    continuity.append_row(row)
                    stored = json.loads((root / "continuity" / "events.jsonl").read_text(encoding="utf-8"))
                    chain_hash = stored.pop("chain_hash")
                    self.assertEqual(stored["prev_hash"], "GENESIS")
                    self.assertEqual(chain_hash, continuity.digest(stored))
                    hashes.append(chain_hash)
            self.assertEqual(hashes[0], hashes[1])
        finally:
            continuity.configure_root(original_root)


if __name__ == "__main__":
    unittest.main()
