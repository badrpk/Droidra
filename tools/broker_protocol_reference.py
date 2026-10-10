"""Offline *reference* request validator, NOT Android caller authentication.

This module is intentionally side-effect free and must never grant runtime
authority. The future Android broker must authenticate the caller using OS
identity before passing an authenticated session into its own policy engine.
"""
import re
from dataclasses import dataclass

PROTOCOL_VERSION = 1
OPERATIONS = frozenset({
    "health", "stage_candidate", "verify_candidate",
    "get_receipt", "discard_candidate",
})
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
MAX_BYTES = 1024 * 1024
MAX_PATHS = 32


class PolicyDenied(ValueError):
    pass


@dataclass(frozen=True)
class Session:
    # This is test data, not proof of an Android UID or package signature.
    session_id: str
    challenge: str
    authenticated: bool


def validate_request(request, session, seen_request_ids=frozenset()):
    """Validate a pure data envelope; return an immutable normalized tuple."""
    if not isinstance(session, Session) or not session.authenticated:
        raise PolicyDenied("Caller not authenticated")
    if not isinstance(request, dict):
        raise PolicyDenied("Invalid envelope")
    fields = {
        "version", "request_id", "operation", "session_id", "challenge",
        "base_digest", "candidate_digest", "paths", "byte_count",
    }
    if set(request) != fields:
        raise PolicyDenied("Unknown or missing envelope field")
    if type(request["version"]) is not int or request["version"] != PROTOCOL_VERSION:
        raise PolicyDenied("Unsupported protocol")
    for name in ("request_id", "session_id", "challenge"):
        value = request[name]
        if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
            raise PolicyDenied("Invalid identifier")
    if request["session_id"] != session.session_id or request["challenge"] != session.challenge:
        raise PolicyDenied("Session mismatch")
    if request["request_id"] in seen_request_ids:
        raise PolicyDenied("Replay")
    operation = request["operation"]
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise PolicyDenied("Operation not permitted")
    for name in ("base_digest", "candidate_digest"):
        digest = request[name]
        if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
            raise PolicyDenied("Invalid digest")
    size = request["byte_count"]
    if type(size) is not int or not 0 <= size <= MAX_BYTES:
        raise PolicyDenied("Invalid byte count")
    paths = request["paths"]
    if not isinstance(paths, (list, tuple)) or len(paths) > MAX_PATHS:
        raise PolicyDenied("Invalid paths")
    normalized = []
    seen = set()
    for path in paths:
        if not isinstance(path, str) or not path or len(path) > 240:
            raise PolicyDenied("Invalid path")
        if (
            path.startswith("/") or "\\" in path or "\x00" in path
            or any(part in ("", ".", "..") for part in path.split("/"))
        ):
            raise PolicyDenied("Unsafe path")
        # Reject aliasing without attempting filesystem access.
        folded = path.casefold()
        if folded in seen:
            raise PolicyDenied("Duplicate path")
        seen.add(folded)
        normalized.append(path)
    if operation == "stage_candidate" and (not paths or size == 0):
        raise PolicyDenied("Empty staging request")
    if operation != "stage_candidate" and (paths or size):
        raise PolicyDenied("Unexpected payload")
    return (request["request_id"], operation, tuple(normalized),
            request["base_digest"], request["candidate_digest"], size)
