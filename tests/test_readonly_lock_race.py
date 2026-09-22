from pathlib import Path
from unittest.mock import patch

import continuity
from continuity_readonly_lock import readonly_project_lock


def test_readonly_lock_disappearing_between_exists_and_open_is_non_mutating(tmp_path):
    continuity.configure_root(tmp_path)
    lock_path = tmp_path / "continuity" / ".lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_bytes(b"0")

    real_open = Path.open

    def disappearing_open(self, *args, **kwargs):
        if self == lock_path:
            lock_path.unlink()
            raise FileNotFoundError(str(lock_path))
        return real_open(self, *args, **kwargs)

    with patch.object(Path, "open", disappearing_open):
        with readonly_project_lock():
            pass

    assert not lock_path.exists()
