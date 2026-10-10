import unittest
from dataclasses import replace
from broker_protocol_reference import Session, PolicyDenied
from broker_state_reference import Model, apply, check_receipts

SESSION = Session("session_1", "challenge_1", True)
BASE = "a" * 64
CANDIDATE = "b" * 64

def request(operation, number, **changes):
    result = dict(version=1, request_id=f"request_{number}", operation=operation,
        session_id=SESSION.session_id, challenge=SESSION.challenge,
        base_digest=BASE, candidate_digest=CANDIDATE,
        paths=["src/file.py"] if operation == "stage_candidate" else [],
        byte_count=8 if operation == "stage_candidate" else 0)
    result.update(changes)
    return result

class BrokerStateReferenceTests(unittest.TestCase):
    def staged(self):
        return apply(Model(), request("stage_candidate", 1), SESSION)[0]

    def verified(self):
        return apply(self.staged(), request("verify_candidate", 2),
                     SESSION, evidence=b"independent evidence", verifier_ok=True)[0]

    def denied_unchanged(self, model, req, **kwargs):
        before = model
        with self.assertRaises(PolicyDenied):
            apply(model, req, SESSION, **kwargs)
        self.assertEqual(model, before)

    def test_stage(self):
        model = self.staged()
        self.assertEqual(model.state, "STAGED")
        self.assertTrue(check_receipts(model.receipts))

    def test_verify_and_receipt(self):
        model = self.verified()
        self.assertEqual(model.state, "VERIFIED")
        self.assertEqual(model.sequence, 2)
        self.assertTrue(check_receipts(model.receipts))

    def test_receipt_query(self):
        model, receipt = apply(self.verified(), request("get_receipt", 3), SESSION)
        self.assertEqual(model.state, "VERIFIED")
        self.assertEqual(receipt.evidence_digest, model.receipts[-2].evidence_digest)

    def test_discard(self):
        model, receipt = apply(self.verified(), request("discard_candidate", 3), SESSION)
        self.assertEqual(model.state, "EMPTY")
        self.assertEqual(model.candidate_digest, "")
        self.assertTrue(check_receipts(model.receipts))

    def test_replay_rejected(self):
        self.denied_unchanged(self.staged(), request("stage_candidate", 1))

    def test_conflicting_stage(self):
        self.denied_unchanged(self.staged(), request("stage_candidate", 2))

    def test_verify_before_stage(self):
        self.denied_unchanged(Model(), request("verify_candidate", 1),
            evidence=b"evidence", verifier_ok=True)

    def test_verifier_crash_or_failure(self):
        for outcome in (None, False):
            self.denied_unchanged(self.staged(), request("verify_candidate", 2),
                evidence=b"evidence", verifier_ok=outcome)

    def test_missing_evidence(self):
        self.denied_unchanged(self.staged(), request("verify_candidate", 2),
            verifier_ok=True)

    def test_changed_digest(self):
        self.denied_unchanged(self.staged(),
            request("verify_candidate", 2, candidate_digest="c" * 64),
            evidence=b"evidence", verifier_ok=True)

    def test_no_promotion(self):
        self.denied_unchanged(self.verified(), request("promote", 3))

    def test_receipt_before_verify(self):
        self.denied_unchanged(self.staged(), request("get_receipt", 2))

    def test_discard_wrong_candidate(self):
        self.denied_unchanged(self.staged(),
            request("discard_candidate", 2, base_digest="c" * 64))

    def test_health_preserves_candidate(self):
        model, receipt = apply(self.staged(), request("health", 2), SESSION)
        self.assertEqual(model.state, "STAGED")
        self.assertTrue(check_receipts(model.receipts))

    def test_tampered_receipt_detected(self):
        model = self.verified()
        altered = replace(model.receipts[0], candidate_digest="c" * 64)
        self.assertFalse(check_receipts((altered,) + model.receipts[1:]))

    def test_missing_receipt_detected(self):
        model = self.verified()
        self.assertFalse(check_receipts(model.receipts[1:]))

    def test_receipt_sequence_monotonic(self):
        model = self.verified()
        self.assertEqual([r.sequence for r in model.receipts], [1, 2])

    def test_restart_does_not_claim_durable_replay(self):
        # An empty fresh model has no durable replay knowledge: intentionally
        # demonstrates the gap that a future persistent backend must close.
        old = self.staged()
        new, _ = apply(Model(), request("stage_candidate", 1), SESSION)
        self.assertEqual(new.state, old.state)
        self.assertNotEqual(id(new), id(old))

if __name__ == "__main__":
    unittest.main()
