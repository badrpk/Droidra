"""Phase 100C offline SQLite challenge consumption reference.

Only suitable for a trusted private local directory with cooperating processes.
Not Android IPC, OS identity attestation, anti-rollback storage, or a security
boundary against a same-UID attacker modifying the database.
"""
import sqlite3
from contextlib import closing
from pathlib import Path
from broker_admission_reference import admit
from broker_protocol_reference import PolicyDenied

class ReplayStore:
    def __init__(self, path):
        self.path = Path(path)

    def initialize(self):
        if not self.path.parent.is_dir():
            raise PolicyDenied("Missing replay directory")
        with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as db:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS consumed (value TEXT PRIMARY KEY NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)")
            db.execute("INSERT OR IGNORE INTO metadata VALUES (1,1)")

    def consume(self, policy, caller, challenge, *, request, now):
        if not self.path.is_file():
            raise PolicyDenied("Replay store unavailable")
        try:
            with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as db:
                db.execute("PRAGMA busy_timeout=10000")
                db.execute("BEGIN IMMEDIATE")
                try:
                    version = db.execute("SELECT version FROM metadata WHERE id=1").fetchone()
                    if version != (1,):
                        raise PolicyDenied("Replay schema unavailable")
                    used = db.execute("SELECT value FROM consumed WHERE value=?",
                                      (challenge.value if hasattr(challenge, "value") else "",)).fetchone()
                    admit(policy, caller, challenge, request=request, now=now,
                          used_challenges={challenge.value} if used else set())
                    db.execute("INSERT INTO consumed(value) VALUES (?)", (challenge.value,))
                    db.execute("COMMIT")
                    return True
                except BaseException:
                    db.execute("ROLLBACK")
                    raise
        except sqlite3.Error as exc:
            raise PolicyDenied("Replay persistence failed") from exc
