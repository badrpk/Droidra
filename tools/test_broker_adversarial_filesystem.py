"""Adversarial offline filesystem probes. Regression tests for previously observed filesystem gaps.

No production filesystem or APK is touched. Each test uses a temporary tree.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from broker_protocol_reference import PolicyDenied, Session
from broker_locked_reference import LockedReference

SESSION = Session("session_1", "challenge_1", True)
def req(n=1):
    return dict(version=1, request_id=f"request_{n}",
        operation="stage_candidate", session_id=SESSION.session_id,
        challenge=SESSION.challenge, base_digest="a"*64,
        candidate_digest="b"*64, paths=["src/a.py"], byte_count=1)

class AdversarialFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "broker"
        self.store = LockedReference(self.directory)
        self.store.initialize()

    def test_lock_symlink_denied(self):
        outside = self.root / "outside-lock"
        outside.write_text("sentinel")
        self.store.lockfile.unlink()
        self.store.lockfile.symlink_to(outside)
        with self.assertRaises(PolicyDenied):
            self.store.transition(req(), SESSION)
        self.assertEqual(outside.read_text(), "sentinel")

    def test_state_symlink_denied_before_transition(self):
        # A state symlink must be rejected before processing.
        outside = self.root / "outside-state"
        outside.write_bytes(self.store.file.read_bytes())
        self.store.file.unlink()
        self.store.file.symlink_to(outside)
        with self.assertRaises(PolicyDenied):
            self.store.transition(req(), SESSION)

    def test_lock_inode_replacement_denied(self):
        # Recheck locked inode identity after acquiring flock.
        replacement = self.root / "replacement-lock"
        replacement.write_bytes(b"")
        original = os.stat(self.store.lockfile).st_ino
        real_flock = __import__("fcntl").flock
        def swapped(fd, mode):
            real_flock(fd, mode)
            os.replace(replacement, self.store.lockfile)
        with patch("broker_locked_reference.fcntl.flock", side_effect=swapped):
            with self.assertRaises(PolicyDenied):
                self.store.transition(req(), SESSION)
        self.assertNotEqual(original, os.stat(self.store.lockfile).st_ino)

    def test_state_inode_swap_during_validation_denied(self):
        # Detect a state pathname swap between stat and open.
        outside = self.root / "replacement-state"
        outside.write_bytes(self.store.file.read_bytes())
        original_open = Path.open
        swapped = [False]
        def intercept(path, *args, **kwargs):
            if Path(path) == self.store.file and not swapped[0]:
                swapped[0] = True
                os.replace(outside, self.store.file)
            return original_open(path, *args, **kwargs)
        with patch("pathlib.Path.open", intercept):
            with self.assertRaises(PolicyDenied):
                self.store.transition(req(), SESSION)

    def test_lock_failure_keeps_state(self):
        before = self.store.file.read_bytes()
        with patch("broker_locked_reference.fcntl.flock", side_effect=OSError("denied")):
            with self.assertRaises(PolicyDenied):
                self.store.transition(req(), SESSION)
        self.assertEqual(before, self.store.file.read_bytes())

    def test_corrupted_receipt_keeps_state(self):
        self.store.transition(req(), SESSION)
        state = self.store.file.read_bytes()
        self.store.file.write_bytes(state.replace(b'"sequence":1', b'"sequence":9'))
        before = self.store.file.read_bytes()
        with self.assertRaises(PolicyDenied):
            self.store.transition(req(2), SESSION)
        self.assertEqual(before, self.store.file.read_bytes())

    def test_initialization_rejects_existing_state(self):
        before = self.store.file.read_bytes()
        with self.assertRaises(PolicyDenied):
            self.store.initialize()
        self.assertEqual(before, self.store.file.read_bytes())

if __name__ == "__main__":
    unittest.main()
