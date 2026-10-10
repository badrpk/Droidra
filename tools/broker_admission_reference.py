"""Phase 100B: offline admission policy model. NOT Binder identity authentication.

The adapter must supply CallerEvidence from an OS-verified Binder identity in
a future, separately reviewed implementation. Constructing this dataclass in
Python is not proof of an Android caller's identity.
"""
from dataclasses import dataclass
from broker_protocol_reference import PolicyDenied

@dataclass(frozen=True)
class CallerEvidence:
    uid: int
    user_id: int
    packages: tuple[str, ...]
    signature_digest: str
    os_verified: bool

@dataclass(frozen=True)
class AdmissionPolicy:
    uid: int
    user_id: int
    package: str
    signature_digest: str
    max_request_bytes: int = 65536

@dataclass(frozen=True)
class Challenge:
    value: str
    uid: int
    user_id: int
    operation: str
    request_digest: str
    expires_at: int

ALLOWED = frozenset(("health", "stage_candidate", "verify_candidate", "get_receipt", "discard_candidate"))

def admit(policy, caller, challenge, *, request, now, used_challenges):
    """Validate untrusted envelope against adapter-supplied evidence; no side effects.

    The caller of this function owns persistent replay recording. This model
    only decides admission; it never issues an authoritative Android receipt.
    """
    if not isinstance(policy, AdmissionPolicy) or not isinstance(caller, CallerEvidence):
        raise PolicyDenied("Invalid admission evidence")
    if type(caller.uid) is not int or type(caller.user_id) is not int or not caller.os_verified:
        raise PolicyDenied("Caller identity not verified")
    if caller.uid != policy.uid or caller.user_id != policy.user_id:
        raise PolicyDenied("Unauthorized UID or profile")
    if caller.packages != (policy.package,) or caller.signature_digest != policy.signature_digest:
        raise PolicyDenied("Ambiguous or untrusted package identity")
    if not isinstance(request, dict) or set(request) != {"operation", "digest", "size"}:
        raise PolicyDenied("Malformed request")
    operation, digest, size = request["operation"], request["digest"], request["size"]
    if not isinstance(operation, str) or operation not in ALLOWED:
        raise PolicyDenied("Forbidden operation")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise PolicyDenied("Invalid request digest")
    if type(size) is not int or not 0 <= size <= policy.max_request_bytes:
        raise PolicyDenied("Invalid request size")
    if not isinstance(challenge, Challenge) or not isinstance(challenge.value, str) or len(challenge.value) < 16:
        raise PolicyDenied("Missing challenge")
    if type(now) is not int or type(challenge.expires_at) is not int or now >= challenge.expires_at:
        raise PolicyDenied("Expired challenge")
    if (challenge.uid != caller.uid or challenge.user_id != caller.user_id
        or challenge.operation != operation or challenge.request_digest != digest):
        raise PolicyDenied("Challenge binding mismatch")
    if challenge.value in used_challenges:
        raise PolicyDenied("Replay")
    return True
