"""Offline transactional replay tests; trusted private filesystem assumption."""
import concurrent.futures
import sqlite3
import tempfile
import unittest
import gc
import warnings
from contextlib import closing
from pathlib import Path
from dataclasses import replace
from broker_protocol_reference import PolicyDenied
from broker_replay_reference import ReplayStore
from test_broker_admission_reference import POLICY, CALLER, CHALLENGE, REQUEST

class ReplayStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "replay.sqlite"
        self.store = ReplayStore(self.path)
        self.store.initialize()

    def consume(self, challenge=CHALLENGE, caller=CALLER, request=REQUEST, now=100):
        return self.store.consume(POLICY, caller, challenge, request=request, now=now)

    def test_connections_closed_without_resource_warnings(self):
        gc.collect()  # Drain objects left by earlier tests before capturing warnings.
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", ResourceWarning)
            self.consume()
            with self.assertRaises(PolicyDenied):
                self.consume()
            gc.collect()
        leaked = [w for w in captured if issubclass(w.category, ResourceWarning)
                  and "unclosed database" in str(w.message)]
        self.assertEqual(leaked, [])

    def test_first_consumption(self):
        self.assertTrue(self.consume())

    def test_replay_denied(self):
        self.consume()
        with self.assertRaises(PolicyDenied):
            self.consume()

    def test_restart_replay_denied(self):
        self.consume()
        reopened = ReplayStore(self.path)
        with self.assertRaises(PolicyDenied):
            reopened.consume(POLICY, CALLER, CHALLENGE, request=REQUEST, now=100)

    def test_invalid_request_does_not_consume(self):
        with self.assertRaises(PolicyDenied):
            self.consume(request={**REQUEST, "operation": "promote"})
        self.assertTrue(self.consume())

    def test_unverified_caller_does_not_consume(self):
        with self.assertRaises(PolicyDenied):
            self.consume(caller=replace(CALLER, os_verified=False))
        self.assertTrue(self.consume())

    def test_expired_challenge_does_not_consume(self):
        with self.assertRaises(PolicyDenied):
            self.consume(now=CHALLENGE.expires_at)
        self.assertTrue(self.consume())

    def test_concurrent_same_challenge_at_most_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures = [pool.submit(self.consume) for _ in range(24)]
            outcomes = []
            for future in futures:
                try:
                    outcomes.append(future.result())
                except PolicyDenied:
                    outcomes.append(False)
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(outcomes.count(False), 23)

    def test_independent_challenges(self):
        self.assertTrue(self.consume())
        self.assertTrue(self.consume(challenge=replace(CHALLENGE, value="another-challenge-123456")))

    def test_missing_database_denied(self):
        self.path.unlink()
        with self.assertRaises(PolicyDenied):
            self.consume()

    def test_corrupt_schema_denied(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("DELETE FROM metadata")
        with self.assertRaises(PolicyDenied):
            self.consume()

    def test_insert_failure_rolls_back(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER block_insert BEFORE INSERT ON consumed BEGIN SELECT RAISE(FAIL, 'blocked'); END")
        with self.assertRaises(PolicyDenied):
            self.consume()
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM consumed").fetchone()[0], 0)

if __name__ == "__main__":
    unittest.main()
