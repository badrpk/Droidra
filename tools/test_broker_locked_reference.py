import multiprocessing
import tempfile
import unittest
from unittest.mock import patch
from broker_protocol_reference import PolicyDenied, Session
from broker_locked_reference import LockedReference

SESSION = Session("session_1", "challenge_1", True)
def request(op, n):
    return dict(version=1, request_id=f"request_{n}", operation=op,
        session_id=SESSION.session_id, challenge=SESSION.challenge,
        base_digest="a"*64, candidate_digest="b"*64,
        paths=["a.py"] if op == "stage_candidate" else [],
        byte_count=1 if op == "stage_candidate" else 0)

def worker(directory, start, queue, number):
    start.wait()
    try:
        LockedReference(directory).transition(request("stage_candidate", number), SESSION)
        queue.put("accepted")
    except PolicyDenied:
        queue.put("denied")

class LockedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = LockedReference(self.tmp.name)
        self.store.initialize()

    def test_normal_transition(self):
        self.store.transition(request("stage_candidate", 1), SESSION)
        self.assertEqual(self.store.load().sequence, 1)

    def test_replay_after_reopen(self):
        self.store.transition(request("stage_candidate", 1), SESSION)
        with self.assertRaises(PolicyDenied):
            LockedReference(self.tmp.name).transition(request("stage_candidate", 1), SESSION)

    def test_competing_processes(self):
        context = multiprocessing.get_context("spawn")
        start = context.Event()
        queue = context.Queue()
        workers = [context.Process(target=worker,
            args=(self.tmp.name, start, queue, n)) for n in (1, 2)]
        for p in workers: p.start()
        try:
            start.set()
            outcomes = [queue.get(timeout=20) for _ in workers]
            for p in workers: p.join(timeout=20)
            self.assertEqual(sorted(outcomes), ["accepted", "denied"])
            self.assertTrue(all(p.exitcode == 0 for p in workers))
            self.assertEqual(self.store.load().sequence, 1)
        finally:
            for p in workers:
                if p.is_alive():
                    p.terminate()
                    p.join()

    def test_lock_failure_preserves_state(self):
        before = self.store.file.read_bytes()
        with patch("broker_locked_reference.fcntl.flock", side_effect=OSError("lock failed")):
            with self.assertRaises(PolicyDenied):
                self.store.transition(request("stage_candidate", 1), SESSION)
        self.assertEqual(before, self.store.file.read_bytes())

    def test_missing_directory_fails_closed(self):
        with self.assertRaises(PolicyDenied):
            LockedReference(self.tmp.name + "/missing").transition(
                request("stage_candidate", 1), SESSION)

    def test_no_reinitialization(self):
        with self.assertRaises(PolicyDenied):
            self.store.initialize()

    def test_lock_file_persists(self):
        self.store.transition(request("stage_candidate", 1), SESSION)
        self.assertTrue(self.store.lockfile.exists())

if __name__ == "__main__":
    unittest.main()
