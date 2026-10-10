"""Offline descriptor-relative POSIX transaction reference, NOT an Android security boundary.

Requires a trusted private directory and cooperating writers. An attacker with
write access to that directory can still race a final check or replace lock
inodes. No APK, IPC, promotion, or production filesystem authority is provided.
"""
import fcntl
import json
import os
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path
from broker_protocol_reference import PolicyDenied
from broker_durable_reference import DurableReference, decode, encode
from broker_state_reference import Model

_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)

class LockedReference(DurableReference):
    def __init__(self, directory):
        super().__init__(directory)
        self.lockfile = Path(directory) / ".broker.lock"
        self._dirfd = None
        self._state_pin = None

    def _assert_directory(self):
        try:
            named = self.directory.lstat()
            opened = os.fstat(self._dirfd)
        except OSError as exc:
            raise PolicyDenied("Broker directory unavailable") from exc
        if (not stat.S_ISDIR(named.st_mode)
                or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)):
            raise PolicyDenied("Broker directory replaced")

    def _entry(self, name):
        try:
            info = os.stat(name, dir_fd=self._dirfd, follow_symlinks=False)
        except OSError as exc:
            raise PolicyDenied("Broker entry unavailable") from exc
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PolicyDenied("Unsafe broker entry")
        return (info.st_dev, info.st_ino)

    @contextmanager
    def _transaction_lock(self):
        if self._dirfd is not None:
            raise PolicyDenied("Nested broker transaction")
        try:
            directory_fd = os.open(self.directory, os.O_RDONLY | _DIRECTORY | _NOFOLLOW | _CLOEXEC)
        except OSError as exc:
            raise PolicyDenied("Missing or unsafe broker directory") from exc
        self._dirfd = directory_fd
        lock_fd = None
        try:
            self._assert_directory()
            lock_fd = os.open(".broker.lock", os.O_RDWR | os.O_CREAT | _NOFOLLOW | _CLOEXEC,
                              0o600, dir_fd=directory_fd)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            self._assert_directory()
            pin = self._entry(".broker.lock")
            opened = os.fstat(lock_fd)
            if pin != (opened.st_dev, opened.st_ino):
                raise PolicyDenied("Lock inode changed")
            yield
        except OSError as exc:
            raise PolicyDenied("Broker lock unavailable") from exc
        finally:
            self._state_pin = None
            if lock_fd is not None:
                os.close(lock_fd)
            self._dirfd = None
            os.close(directory_fd)

    def _identity(self):
        if self._dirfd is None:
            return super()._identity()
        self._assert_directory()
        return self._entry("state.json")

    def load(self):
        if self._dirfd is None:
            return super().load()
        pin = self._identity()
        try:
            fd = os.open("state.json", os.O_RDONLY | _NOFOLLOW | _CLOEXEC,
                         dir_fd=self._dirfd)
            with os.fdopen(fd, "rb") as stream:
                opened = os.fstat(stream.fileno())
                if pin != (opened.st_dev, opened.st_ino):
                    raise PolicyDenied("State changed during open")
                payload = stream.read(8 * 1024 * 1024 + 1)
            if self._identity() != pin:
                raise PolicyDenied("State changed during read")
            if len(payload) > 8 * 1024 * 1024:
                raise PolicyDenied("Oversized state")
            return decode(json.loads(payload.decode("utf-8")))
        except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            raise PolicyDenied("State missing or corrupt") from exc

    def _write(self, model, create_only=False):
        if self._dirfd is None:
            return super()._write(model, create_only=create_only)
        self._assert_directory()
        if not create_only:
            if self._state_pin is None or self._identity() != self._state_pin:
                raise PolicyDenied("State changed before commit")
        payload = (json.dumps(encode(model), sort_keys=True, separators=(",", ":")) + "\n").encode()
        temporary = ".state-" + secrets.token_hex(16)
        temp_created = False
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | _CLOEXEC,
                         0o600, dir_fd=self._dirfd)
            temp_created = True
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self._assert_directory()
            if create_only:
                fd = os.open("state.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | _CLOEXEC,
                             0o600, dir_fd=self._dirfd)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            else:
                if self._identity() != self._state_pin:
                    raise PolicyDenied("State changed during write")
                os.replace(temporary, "state.json",
                           src_dir_fd=self._dirfd, dst_dir_fd=self._dirfd)
                temp_created = False
            os.fsync(self._dirfd)
        except OSError as exc:
            raise PolicyDenied("Broker write unavailable") from exc
        finally:
            if temp_created:
                try:
                    os.unlink(temporary, dir_fd=self._dirfd)
                except FileNotFoundError:
                    pass

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with self._transaction_lock():
            # No pathname-based exists() check; exclusive creation is authoritative.
            self._write(Model(), create_only=True)

    def transition(self, request, session, **kwargs):
        with self._transaction_lock():
            self._state_pin = self._identity()
            return super().transition(request, session, **kwargs)
