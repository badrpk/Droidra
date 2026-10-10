"""Phase 100B negative admission tests; mock evidence is not real Binder identity."""
import unittest
from dataclasses import replace
from broker_protocol_reference import PolicyDenied
from broker_admission_reference import CallerEvidence, AdmissionPolicy, Challenge, admit

DIGEST = "a" * 64
POLICY = AdmissionPolicy(10234, 0, "com.example.proposer", "b" * 64)
CALLER = CallerEvidence(10234, 0, ("com.example.proposer",), "b" * 64, True)
CHALLENGE = Challenge("challenge-value-123456", 10234, 0, "health", DIGEST, 200)
REQUEST = {"operation": "health", "digest": DIGEST, "size": 32}

class CallerAdmissionTests(unittest.TestCase):
    def check_denied(self, *, policy=POLICY, caller=CALLER, challenge=CHALLENGE,
                     request=REQUEST, now=100, used=()):
        with self.assertRaises(PolicyDenied):
            admit(policy, caller, challenge, request=request, now=now, used_challenges=used)

    def test_valid_mock_evidence(self):
        self.assertTrue(admit(POLICY, CALLER, CHALLENGE,
                              request=REQUEST, now=100, used_challenges=set()))

    def test_unverified_identity(self):
        self.check_denied(caller=replace(CALLER, os_verified=False))

    def test_unauthorized_uid(self):
        self.check_denied(caller=replace(CALLER, uid=10235))

    def test_cross_profile(self):
        self.check_denied(caller=replace(CALLER, user_id=10))

    def test_shared_uid_ambiguous(self):
        self.check_denied(caller=replace(CALLER, packages=("com.example.proposer", "com.attacker")))

    def test_spoofed_package(self):
        self.check_denied(caller=replace(CALLER, packages=("com.attacker",)))

    def test_wrong_signature(self):
        self.check_denied(caller=replace(CALLER, signature_digest="c" * 64))

    def test_expired_challenge(self):
        self.check_denied(now=200)

    def test_replayed_challenge(self):
        self.check_denied(used={CHALLENGE.value})

    def test_wrong_challenge_binding(self):
        self.check_denied(challenge=replace(CHALLENGE, request_digest="d" * 64))

    def test_wrong_challenge_uid(self):
        self.check_denied(challenge=replace(CHALLENGE, uid=10000))

    def test_forbidden_operation(self):
        self.check_denied(request={**REQUEST, "operation": "promote"})

    def test_oversized_request(self):
        self.check_denied(request={**REQUEST, "size": 65537})

    def test_boolean_size(self):
        self.check_denied(request={**REQUEST, "size": True})

    def test_unknown_field(self):
        self.check_denied(request={**REQUEST, "claimed_uid": 10234})

    def test_malformed_digest(self):
        self.check_denied(request={**REQUEST, "digest": "x" * 64})

    def test_forged_verifier_claim(self):
        self.check_denied(request={**REQUEST, "verifier_ok": True})

    def test_negative_uid(self):
        self.check_denied(caller=replace(CALLER, uid=-1))

    def test_non_integer_time(self):
        self.check_denied(now="100")

if __name__ == "__main__":
    unittest.main()
