import unittest
from broker_protocol_reference import Session, PolicyDenied, validate_request, OPERATIONS, MAX_BYTES

SESSION = Session("session_1", "challenge_1", True)
DIGEST = "a" * 64

def envelope(operation="health", **changes):
    data = dict(version=1, request_id="request_1", operation=operation,
        session_id=SESSION.session_id, challenge=SESSION.challenge,
        base_digest=DIGEST, candidate_digest=DIGEST,
        paths=["src/ok.py"] if operation == "stage_candidate" else [],
        byte_count=1 if operation == "stage_candidate" else 0)
    data.update(changes)
    return data

class BrokerProtocolReferenceTests(unittest.TestCase):
    def denied(self, data, session=SESSION, seen=frozenset()):
        with self.assertRaises(PolicyDenied):
            validate_request(data, session, seen)

    def test_allowlist(self):
        for operation in OPERATIONS:
            with self.subTest(operation=operation):
                self.assertEqual(validate_request(envelope(operation), SESSION)[1], operation)

    def test_unauthenticated(self):
        self.denied(envelope(), Session("session_1", "challenge_1", False))

    def test_forged_session_type(self):
        self.denied(envelope(), {"authenticated": True})

    def test_replay(self):
        self.denied(envelope(), seen={"request_1"})

    def test_session_mismatch(self):
        self.denied(envelope(session_id="other"))

    def test_challenge_mismatch(self):
        self.denied(envelope(challenge="other"))

    def test_forbidden_operation(self):
        self.denied(envelope(operation="promote"))

    def test_shell_operation(self):
        self.denied(envelope(operation="run_shell"))

    def test_unknown_field(self):
        self.denied(envelope(extra="untrusted"))

    def test_missing_field(self):
        data = envelope()
        del data["candidate_digest"]
        self.denied(data)

    def test_wrong_version(self):
        self.denied(envelope(version=2))
        self.denied(envelope(version=True))

    def test_invalid_digest(self):
        self.denied(envelope(candidate_digest="0" * 63))

    def test_oversized_content(self):
        self.denied(envelope("stage_candidate", byte_count=MAX_BYTES + 1))

    def test_negative_or_boolean_size(self):
        self.denied(envelope(byte_count=-1))
        self.denied(envelope(byte_count=True))

    def test_absolute_path(self):
        self.denied(envelope("stage_candidate", paths=["/tmp/escape"]))

    def test_parent_traversal(self):
        self.denied(envelope("stage_candidate", paths=["src/../escape"]))

    def test_empty_segment(self):
        self.denied(envelope("stage_candidate", paths=["src//escape"]))

    def test_backslash(self):
        self.denied(envelope("stage_candidate", paths=["src\\escape"]))

    def test_case_alias(self):
        self.denied(envelope("stage_candidate", paths=["src/A.py", "src/a.py"]))

    def test_too_many_paths(self):
        self.denied(envelope("stage_candidate", paths=[f"src/{i}" for i in range(33)]))

    def test_stage_requires_content(self):
        self.denied(envelope("stage_candidate", byte_count=0))

    def test_read_only_rejects_payload(self):
        self.denied(envelope(paths=["src/ok.py"]))

    def test_valid_stage(self):
        self.assertEqual(validate_request(envelope("stage_candidate"), SESSION)[2], ("src/ok.py",))

if __name__ == "__main__":
    unittest.main()
