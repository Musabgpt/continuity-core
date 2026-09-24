import unittest

import continuity


class TransactionChecksumCanonicalContractTests(unittest.TestCase):
    def test_transaction_checksum_is_insertion_order_invariant(self):
        left = {
            "txid": "tx-1",
            "state": {"revision": 7, "status": "active"},
            "event": {"type": "success", "message": "ok"},
        }
        right = {
            "event": {"message": "ok", "type": "success"},
            "state": {"status": "active", "revision": 7},
            "txid": "tx-1",
        }
        self.assertEqual(continuity.digest(left), continuity.digest(right))
        self.assertEqual(len(continuity.digest(left)), 64)


if __name__ == "__main__":
    unittest.main()
