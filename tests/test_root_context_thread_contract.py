import tempfile
import threading
import time
import unittest
from pathlib import Path

import continuity
from continuity_root import isolated_root


class RootContextThreadContractTests(unittest.TestCase):
    def test_isolated_root_serializes_concurrent_scopes(self):
        original = continuity.ROOT
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first"
            second = Path(temp_dir) / "second"
            observed = []
            errors = []
            active = 0
            peak_active = 0
            state_lock = threading.Lock()

            def worker(target):
                nonlocal active, peak_active
                try:
                    with isolated_root(continuity, target):
                        with state_lock:
                            active += 1
                            peak_active = max(peak_active, active)
                            observed.append(continuity.ROOT)
                        time.sleep(0.02)
                        with state_lock:
                            active -= 1
                            self.assertEqual(continuity.ROOT, target.resolve())
                except BaseException as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=worker, args=(first,)),
                threading.Thread(target=worker, args=(second,)),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            self.assertEqual(peak_active, 1)
            self.assertEqual(set(observed), {first.resolve(), second.resolve()})
            self.assertEqual(continuity.ROOT, original)


if __name__ == "__main__":
    unittest.main()
