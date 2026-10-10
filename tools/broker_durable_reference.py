"""Offline single-process crash-consistency reference; not a security boundary."""
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from broker_protocol_reference import PolicyDenied
from broker_state_reference import Model, Receipt, apply, check_receipts

def encode(model):
    return {"schema": 1, "model": {
        "state": model.state, "base_digest": model.base_digest,
        "candidate_digest": model.candidate_digest, "sequence": model.sequence,
        "previous_digest": model.previous_digest, "seen": sorted(model.seen),
        "receipts": [asdict(r) for r in model.receipts]}}

def decode(value):
    if type(value) is not dict or set(value) != {"schema", "model"} or type(value["schema"]) is not int or value["schema"] != 1:
        raise PolicyDenied("Invalid schema")
    raw = value["model"]
    if type(raw) is not dict or set(raw) != set(Model.__dataclass_fields__):
        raise PolicyDenied("Invalid state shape")
    if type(raw["receipts"]) is not list or type(raw["seen"]) is not list:
        raise PolicyDenied("Invalid collections")
    if any(type(r) is not dict or set(r) != set(Receipt.__dataclass_fields__) for r in raw["receipts"]):
        raise PolicyDenied("Invalid receipt shape")
    if any(type(r["sequence"]) is not int or any(type(v) is not str for k,v in r.items() if k != "sequence") for r in raw["receipts"]):
        raise PolicyDenied("Invalid receipt types")
    if any(type(x) is not str for x in raw["seen"]) or len(raw["seen"]) != len(set(raw["seen"])):
        raise PolicyDenied("Invalid replay index")
    if type(raw["sequence"]) is not int or raw["sequence"] < 0 or raw["sequence"] != len(raw["receipts"]):
        raise PolicyDenied("Invalid sequence")
    if any(type(raw[k]) is not str for k in ("state", "base_digest", "candidate_digest", "previous_digest")):
        raise PolicyDenied("Invalid state types")
    receipts = tuple(Receipt(**r) for r in raw["receipts"])
    model = Model(raw["state"], raw["base_digest"], raw["candidate_digest"],
                  raw["sequence"], raw["previous_digest"], receipts, frozenset(raw["seen"]))
    if not check_receipts(receipts) or model.previous_digest != (receipts[-1].receipt_digest if receipts else "0"*64):
        raise PolicyDenied("Broken receipt chain")
    if model.seen != frozenset(r.request_id for r in receipts):
        raise PolicyDenied("Replay index mismatch")
    if model.state not in {"EMPTY", "STAGED", "VERIFIED"}:
        raise PolicyDenied("Invalid state")
    if model.state == "EMPTY" and (model.base_digest or model.candidate_digest):
        raise PolicyDenied("Invalid empty candidate")
    if model.state != "EMPTY" and (not receipts or not model.base_digest or not model.candidate_digest):
        raise PolicyDenied("Invalid active candidate")
    if receipts:
        last = receipts[-1]
        if model.state != last.state or (model.state != "EMPTY" and (model.base_digest,model.candidate_digest) != (last.base_digest,last.candidate_digest)):
            raise PolicyDenied("State/receipt mismatch")
    return model

class DurableReference:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.file = self.directory / "state.json"

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.file.exists():
            raise PolicyDenied("Already provisioned")
        self._write(Model(), create_only=True)

    def load(self):
        try:
            with self.file.open("rb") as stream:
                data = stream.read(8*1024*1024+1)
            if len(data) > 8*1024*1024:
                raise PolicyDenied("Oversized state")
            return decode(json.loads(data.decode("utf-8")))
        except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            raise PolicyDenied("State missing or corrupt") from exc

    def _write(self, model, create_only=False):
        payload = (json.dumps(encode(model), sort_keys=True, separators=(",", ":"))+"\n").encode()
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=".state-", dir=self.directory)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if create_only:
                os.link(temporary, self.file)
            else:
                os.replace(temporary, self.file)
            fd = os.open(self.directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            if temporary is not None:
                try: os.unlink(temporary)
                except FileNotFoundError: pass

    def transition(self, request, session, **kwargs):
        before = self.load()
        after, receipt = apply(before, request, session, **kwargs)
        self._write(after)
        return receipt
