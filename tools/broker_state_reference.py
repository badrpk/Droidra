"""Offline-only deterministic broker state machine. No filesystem or Android IPC.

This is a reference model, NOT a runtime broker, authentication layer,
durable replay database, or permission to install/promote an APK.
"""
from dataclasses import dataclass, replace
from hashlib import sha256
from broker_protocol_reference import PolicyDenied, validate_request

@dataclass(frozen=True)
class Receipt:
    sequence: int
    request_id: str
    operation: str
    state: str
    base_digest: str
    candidate_digest: str
    evidence_digest: str
    previous_digest: str
    receipt_digest: str

@dataclass(frozen=True)
class Model:
    state: str = "EMPTY"
    base_digest: str = ""
    candidate_digest: str = ""
    sequence: int = 0
    previous_digest: str = "0" * 64
    receipts: tuple = ()
    seen: frozenset = frozenset()

def _digest(*parts):
    return sha256("\x00".join(str(x) for x in parts).encode("utf-8")).hexdigest()

def apply(model, request, session, *, evidence=None, verifier_ok=None):
    """Pure transition. On any denial the caller's original model is unchanged.

    Replay is modeled in immutable memory only; crash-safe durability is NOT
    provided. Verification evidence is an untrusted test input here.
    """
    if not isinstance(model, Model):
        raise PolicyDenied("Invalid model")
    request_id, operation, paths, base, candidate, size = validate_request(
        request, session, model.seen
    )
    if operation == "stage_candidate":
        if model.state != "EMPTY":
            raise PolicyDenied("Candidate already active")
        if evidence is not None or verifier_ok is not None:
            raise PolicyDenied("Unexpected verification evidence")
        next_state = "STAGED"
        next_base, next_candidate = base, candidate
        evidence_digest = "0" * 64
    elif operation == "verify_candidate":
        if model.state != "STAGED" or (base, candidate) != (
            model.base_digest, model.candidate_digest
        ):
            raise PolicyDenied("Missing or changed candidate")
        if not isinstance(evidence, bytes) or not evidence:
            raise PolicyDenied("Missing verification evidence")
        if verifier_ok is not True:
            raise PolicyDenied("Verifier unavailable or rejected")
        next_state = "VERIFIED"
        next_base, next_candidate = base, candidate
        evidence_digest = sha256(evidence).hexdigest()
    elif operation == "get_receipt":
        if model.state != "VERIFIED" or (base, candidate) != (
            model.base_digest, model.candidate_digest
        ):
            raise PolicyDenied("No verified candidate")
        if evidence is not None or verifier_ok is not None:
            raise PolicyDenied("Unexpected verification evidence")
        next_state = "VERIFIED"
        next_base, next_candidate = base, candidate
        evidence_digest = model.receipts[-1].evidence_digest
    elif operation == "discard_candidate":
        if model.state not in {"STAGED", "VERIFIED"} or (base, candidate) != (
            model.base_digest, model.candidate_digest
        ):
            raise PolicyDenied("No matching candidate")
        if evidence is not None or verifier_ok is not None:
            raise PolicyDenied("Unexpected verification evidence")
        next_state = "EMPTY"
        next_base, next_candidate = "", ""
        evidence_digest = "0" * 64
    elif operation == "health":
        if evidence is not None or verifier_ok is not None:
            raise PolicyDenied("Unexpected verification evidence")
        next_state = model.state
        next_base, next_candidate = model.base_digest, model.candidate_digest
        evidence_digest = "0" * 64
    else:
        raise PolicyDenied("Operation denied")
    seq = model.sequence + 1
    receipt_digest = _digest(seq, request_id, operation, next_state,
        base, candidate, evidence_digest, model.previous_digest)
    receipt = Receipt(seq, request_id, operation, next_state, base,
        candidate, evidence_digest, model.previous_digest, receipt_digest)
    updated = replace(model, state=next_state, base_digest=next_base,
        candidate_digest=next_candidate, sequence=seq,
        previous_digest=receipt_digest, receipts=model.receipts + (receipt,),
        seen=model.seen | {request_id})
    return updated, receipt

def check_receipts(receipts):
    previous = "0" * 64
    for index, receipt in enumerate(receipts, 1):
        if not isinstance(receipt, Receipt) or receipt.sequence != index:
            return False
        if receipt.previous_digest != previous:
            return False
        expected = _digest(receipt.sequence, receipt.request_id,
            receipt.operation, receipt.state, receipt.base_digest,
            receipt.candidate_digest, receipt.evidence_digest, previous)
        if receipt.receipt_digest != expected:
            return False
        previous = expected
    return True
