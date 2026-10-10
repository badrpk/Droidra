"""Phase 99 offline probes: directory identity and commit-window races.

Expected failures are known gaps, not security acceptance. No production paths.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from broker_protocol_reference import PolicyDenied, Session
from broker_locked_reference import LockedReference

SESSION = Session("session_1", "challenge_1", True)
def request(n=1):
    return dict(version=1, request_id=f"request_{n}",
        operation="stage_candidate", session_id=SESSION.session_id,
        challenge=SESSION.challenge, base_digest="a"*64,
        candidate_digest="b"*64, paths=["src/a.py"], byte_count=1)

class DirectoryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "broker"
        self.store = LockedReference(self.directory)
        self.store.initialize()

    @unittest.expectedFailure
    def test_directory_symlink_rejected(self):
        real = self.root / "real"
        os.rename(self.directory, real)
        self.directory.symlink_to(real, target_is_directory=True)
        with self.assertRaises(PolicyDenied):
            self.store.transition(request(), SESSION)

    @unittest.expectedFailure
    def test_directory_swap_before_commit_rejected(self):
        original_write = self.store._write
        moved = self.root / "moved-broker"
        replacement = self.root / "replacement-broker"
        replacement.mkdir()
        (replacement / "state.json").write_bytes(self.store.file.read_bytes())
        (replacement / ".broker.lock").write_bytes(b"")
        def swap_then_write(*args, **kwargs):
            os.rename(self.directory, moved)
            os.rename(replacement, self.directory)
            return original_write(*args, **kwargs)
        with patch.object(self.store, "_write", side_effect=swap_then_write):
            with self.assertRaises(PolicyDenied):
                self.store.transition(request(), SESSION)

    @unittest.expectedFailure
    def test_state_swap_after_last_check_rejected(self):
        original_write = self.store._write
        replacement = self.root / "replacement-state"
        replacement.write_bytes(self.store.file.read_bytes())
        def swap_then_write(*args, **kwargs):
            os.replace(replacement, self.store.file)
            return original_write(*args, **kwargs)
        with patch.object(self.store, "_write", side_effect=swap_then_write):
            with self.assertRaises(PolicyDenied):
                self.store.transition(request(), SESSION)

    def test_missing_directory_rejected(self):
        absent = LockedReference(self.root / "absent")
        with self.assertRaises(PolicyDenied):
            absent.transition(request(), SESSION)
        self.assertFalse((self.root / "absent").exists())

    def test_ordinary_transition_retains_directory(self):
        before = self.directory.stat()
        self.store.transition(request(), SESSION)
        after = self.directory.stat()
        self.assertEqual((before.st_dev, before.st_ino),
                         (after.st_dev, after.st_ino))

if __name__ == "__main__":
    unittest.main()
