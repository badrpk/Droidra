import json
import tempfile
import unittest
from unittest.mock import patch
from broker_protocol_reference import PolicyDenied, Session
from broker_durable_reference import DurableReference

SESSION = Session("session_1", "challenge_1", True)
def request(operation, number):
    return dict(version=1, request_id=f"request_{number}", operation=operation,
        session_id=SESSION.session_id, challenge=SESSION.challenge,
        base_digest="a"*64, candidate_digest="b"*64,
        paths=["src/a.py"] if operation == "stage_candidate" else [],
        byte_count=1 if operation == "stage_candidate" else 0)

class DurableReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = DurableReference(self.temp.name)
        self.store.initialize()
    def stage(self):
        self.store.transition(request("stage_candidate", 1), SESSION)
    def denied(self):
        with self.assertRaises(PolicyDenied): self.store.load()
    def test_empty(self):
        self.assertEqual(self.store.load().state, "EMPTY")
    def test_no_reinitialize(self):
        with self.assertRaises(PolicyDenied): self.store.initialize()
    def test_restart_replay(self):
        self.stage()
        with self.assertRaises(PolicyDenied):
            DurableReference(self.temp.name).transition(request("stage_candidate", 1), SESSION)
    def test_restart_candidate(self):
        self.stage()
        self.assertEqual(DurableReference(self.temp.name).load().state, "STAGED")
    def test_restart_verified(self):
        self.stage()
        self.store.transition(request("verify_candidate", 2), SESSION, evidence=b"proof", verifier_ok=True)
        self.assertEqual(DurableReference(self.temp.name).load().state, "VERIFIED")
    def test_discard(self):
        self.stage()
        self.store.transition(request("discard_candidate", 2), SESSION)
        self.assertEqual(self.store.load().state, "EMPTY")
    def test_missing_file(self):
        self.store.file.unlink()
        self.denied()
    def test_truncated_file(self):
        self.store.file.write_bytes(b'{"schema":1')
        self.denied()
    def test_receipt_tamper(self):
        self.stage()
        raw = json.loads(self.store.file.read_text())
        raw["model"]["receipts"][0]["candidate_digest"] = "c"*64
        self.store.file.write_text(json.dumps(raw))
        self.denied()
    def test_replay_index_tamper(self):
        self.stage()
        raw = json.loads(self.store.file.read_text())
        raw["model"]["seen"] = []
        self.store.file.write_text(json.dumps(raw))
        self.denied()
    def test_state_tamper(self):
        self.stage()
        raw = json.loads(self.store.file.read_text())
        raw["model"]["state"] = "VERIFIED"
        self.store.file.write_text(json.dumps(raw))
        self.denied()
    def test_denial_preserves_disk(self):
        self.stage()
        before = self.store.file.read_bytes()
        with self.assertRaises(PolicyDenied):
            self.store.transition(request("stage_candidate", 2), SESSION)
        self.assertEqual(before, self.store.file.read_bytes())
    def test_interrupted_replace(self):
        self.stage()
        before = self.store.file.read_bytes()
        with patch("broker_durable_reference.os.replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.store.transition(request("discard_candidate", 2), SESSION)
        self.assertEqual(before, self.store.file.read_bytes())
    def test_schema_rejection(self):
        raw = json.loads(self.store.file.read_text())
        raw["schema"] = 2
        self.store.file.write_text(json.dumps(raw))
        self.denied()
    def test_corruption_never_reinitialized(self):
        self.store.file.write_bytes(b"corrupt")
        with self.assertRaises(PolicyDenied):
            self.store.transition(request("health", 2), SESSION)
        self.assertEqual(self.store.file.read_bytes(), b"corrupt")
if __name__ == "__main__":
    unittest.main()
