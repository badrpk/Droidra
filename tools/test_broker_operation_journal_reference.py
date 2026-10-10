"""Phase 100D offline journal regression tests."""
import concurrent.futures
import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from broker_operation_journal_reference import OperationJournal
from broker_protocol_reference import PolicyDenied
from test_broker_admission_reference import POLICY,CALLER,CHALLENGE,REQUEST

class OperationJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.sqlite"
        self.journal = OperationJournal(self.path)
        self.journal.initialize()

    def begin(self, challenge=CHALLENGE, caller=CALLER, request=REQUEST, now=100):
        return self.journal.begin(POLICY,caller,challenge,request=request,now=now)

    def test_begin_pending(self):
        self.assertTrue(self.begin())
        self.assertEqual(self.journal.inspect(CHALLENGE.value),("PENDING",None))

    def test_restart_preserves_ambiguous_pending(self):
        self.begin()
        reopened=OperationJournal(self.path)
        self.assertEqual(reopened.inspect(CHALLENGE.value),("PENDING",None))
        with self.assertRaises(PolicyDenied):
            reopened.begin(POLICY,CALLER,CHALLENGE,request=REQUEST,now=100)

    def test_duplicate_denied(self):
        self.begin()
        with self.assertRaises(PolicyDenied): self.begin()

    def test_concurrent_at_most_one_pending(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures=[pool.submit(self.begin) for _ in range(24)]
            passed=0
            for f in futures:
                try:
                    passed+=int(f.result())
                except PolicyDenied:
                    pass
        self.assertEqual(passed,1)

    def test_invalid_request_not_journaled(self):
        with self.assertRaises(PolicyDenied):
            self.begin(request={**REQUEST,"operation":"promote"})
        self.assertIsNone(self.journal.inspect(CHALLENGE.value))
        self.assertTrue(self.begin())

    def test_unverified_caller_not_journaled(self):
        with self.assertRaises(PolicyDenied):
            self.begin(caller=replace(CALLER,os_verified=False))
        self.assertIsNone(self.journal.inspect(CHALLENGE.value))

    def test_missing_database_fails_closed(self):
        self.path.unlink()
        with self.assertRaises(PolicyDenied): self.begin()

    def test_corrupt_metadata_fails_closed(self):
        with closing(sqlite3.connect(self.path,isolation_level=None)) as db:
            db.execute("DELETE FROM metadata")
        with self.assertRaises(PolicyDenied): self.begin()

    def test_untrusted_reconcile_denied(self):
        self.begin()
        with self.assertRaises(PolicyDenied):
            self.journal.reconcile(CHALLENGE.value,state="COMPLETED",outcome="ok")
        self.assertEqual(self.journal.inspect(CHALLENGE.value),("PENDING",None))

    def test_completed_is_terminal(self):
        self.begin()
        self.assertTrue(self.journal.reconcile(CHALLENGE.value,state="COMPLETED",outcome="ok",trusted=True))
        self.assertEqual(self.journal.inspect(CHALLENGE.value),("COMPLETED","ok"))
        with self.assertRaises(PolicyDenied):
            self.journal.reconcile(CHALLENGE.value,state="FAILED",outcome="later",trusted=True)

    def test_failed_is_terminal(self):
        self.begin()
        self.assertTrue(self.journal.reconcile(CHALLENGE.value,state="FAILED",outcome="rejected",trusted=True))
        self.assertEqual(self.journal.inspect(CHALLENGE.value),("FAILED","rejected"))

    def test_reconcile_missing_denied(self):
        with self.assertRaises(PolicyDenied):
            self.journal.reconcile("missing",state="COMPLETED",outcome="ok",trusted=True)

    def test_invalid_outcome_denied(self):
        self.begin()
        with self.assertRaises(PolicyDenied):
            self.journal.reconcile(CHALLENGE.value,state="COMPLETED",outcome="",trusted=True)
        self.assertEqual(self.journal.inspect(CHALLENGE.value),("PENDING",None))

    def test_restart_terminal_persists(self):
        self.begin()
        self.journal.reconcile(CHALLENGE.value,state="COMPLETED",outcome="ok",trusted=True)
        self.assertEqual(OperationJournal(self.path).inspect(CHALLENGE.value),("COMPLETED","ok"))

    def test_independent_challenges(self):
        self.begin()
        second=replace(CHALLENGE,value="another-challenge-123456")
        self.assertTrue(self.begin(challenge=second))
        self.assertEqual(self.journal.inspect(second.value),("PENDING",None))

if __name__=="__main__":
    unittest.main()
