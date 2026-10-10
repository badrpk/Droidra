"""Phase 100D offline operation journal. No external operation execution.

A committed PENDING row is ambiguous after interruption and MUST NOT be
automatically retried. Reconciliation requires a separate trusted authority.
This is not an Android IPC, verifier, or exactly-once side-effect guarantee.
"""
import sqlite3
from contextlib import closing
from pathlib import Path
from broker_admission_reference import admit
from broker_protocol_reference import PolicyDenied

class OperationJournal:
    def __init__(self, path):
        self.path = Path(path)

    def initialize(self):
        if not self.path.parent.is_dir():
            raise PolicyDenied("Missing journal directory")
        with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as db:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)")
            db.execute("INSERT OR IGNORE INTO metadata VALUES (1,1)")
            db.execute("""CREATE TABLE IF NOT EXISTS operations (
                challenge TEXT PRIMARY KEY NOT NULL,
                uid INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                digest TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','COMPLETED','FAILED')),
                outcome TEXT
            )""")

    def _connect(self):
        if not self.path.is_file():
            raise PolicyDenied("Journal unavailable")
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    @staticmethod
    def _schema(db):
        if db.execute("SELECT version FROM metadata WHERE id=1").fetchone() != (1,):
            raise PolicyDenied("Journal metadata invalid")

    def begin(self, policy, caller, challenge, *, request, now):
        """Atomically admit and persist PENDING; never execute user operations."""
        try:
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                try:
                    self._schema(db)
                    used = db.execute("SELECT 1 FROM operations WHERE challenge=?",
                                      (challenge.value if hasattr(challenge, "value") else "",)).fetchone()
                    admit(policy, caller, challenge, request=request, now=now,
                          used_challenges={challenge.value} if used else set())
                    db.execute("""INSERT INTO operations
                        (challenge,uid,user_id,operation,digest,state,outcome)
                        VALUES (?,?,?,?,?,'PENDING',NULL)""",
                        (challenge.value,caller.uid,caller.user_id,
                         request["operation"],request["digest"]))
                    db.execute("COMMIT")
                    return True
                except BaseException:
                    db.execute("ROLLBACK")
                    raise
        except sqlite3.Error as exc:
            raise PolicyDenied("Journal write failed") from exc

    def inspect(self, challenge_value):
        """Read state only. PENDING never implies safe-to-retry."""
        try:
            with closing(self._connect()) as db:
                self._schema(db)
                row = db.execute("SELECT state,outcome FROM operations WHERE challenge=?",
                                 (challenge_value,)).fetchone()
                return row
        except sqlite3.Error as exc:
            raise PolicyDenied("Journal read failed") from exc

    def reconcile(self, challenge_value, *, state, outcome, trusted=False):
        """Offline simulation of an independently authorized reconciliation.

        trusted=True is a mock flag, not real proof of verifier identity.
        Only PENDING may transition; no automatic retry or operation execution.
        """
        if trusted is not True or state not in ("COMPLETED", "FAILED"):
            raise PolicyDenied("Reconciliation authority or state invalid")
        if not isinstance(outcome, str) or not outcome or len(outcome) > 256:
            raise PolicyDenied("Invalid outcome")
        try:
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                try:
                    self._schema(db)
                    changed = db.execute("""UPDATE operations SET state=?,outcome=?
                        WHERE challenge=? AND state='PENDING'""",
                        (state,outcome,challenge_value)).rowcount
                    if changed != 1:
                        raise PolicyDenied("Missing, duplicate, or finalized operation")
                    db.execute("COMMIT")
                    return True
                except BaseException:
                    db.execute("ROLLBACK")
                    raise
        except sqlite3.Error as exc:
            raise PolicyDenied("Reconciliation write failed") from exc
