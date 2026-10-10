"""Offline POSIX flock transaction wrapper; not Android IPC or hostile-FS isolation.

All cooperating writers MUST use this wrapper. The lock inode must remain
stable; never unlink lockfile. This model assumes a trusted private directory.
"""
import fcntl
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from broker_protocol_reference import PolicyDenied
from broker_durable_reference import DurableReference

class LockedReference(DurableReference):
    def __init__(self, directory):
        super().__init__(directory)
        self.lockfile = Path(directory) / ".broker.lock"

    @contextmanager
    def _transaction_lock(self):
        # Do not create the directory here: an unprovisioned/missing store
        # must not be silently reconstructed by a transition.
        if not self.directory.is_dir():
            raise PolicyDenied("Missing broker directory")
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self.lockfile, flags, 0o600)
        except OSError as exc:
            raise PolicyDenied("Lock unavailable") from exc
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                opened = os.fstat(fd)
                named = self.lockfile.lstat()
                if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or not stat.S_ISREG(named.st_mode)
                    or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)):
                    raise PolicyDenied("Lock inode changed")
            except OSError as exc:
                raise PolicyDenied("Lock unavailable") from exc
            yield
        finally:
            os.close(fd)

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with self._transaction_lock():
            # Do not call the parent initialize without this lock.
            super().initialize()

    def transition(self, request, session, **kwargs):
        with self._transaction_lock():
            return super().transition(request, session, **kwargs)
