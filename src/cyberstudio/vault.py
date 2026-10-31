"""Encrypted, in-memory SQLite vault.

This proof-of-concept intentionally does NOT claim SQLCipher compatibility.
SQLite is never intentionally written plaintext to disk. Transactions are
serialized and encrypted with AES-256-GCM before an atomic file replacement.
This trades write performance for simple portable at-rest encryption.
"""
from __future__ import annotations

import contextlib
import hmac
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Iterator

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from filelock import FileLock, Timeout

MAGIC = b"CYBERSTUDIO-VAULT\x01"
SALT_SIZE = 16
NONCE_SIZE = 12
KDF_TIME = 3
KDF_MEMORY_KIB = 65536
KDF_PARALLELISM = 2


class VaultError(Exception):
    """Base error for vault storage."""


class VaultAuthenticationError(VaultError):
    """Wrong passphrase or tampered/corrupt file; don't reveal which."""


class Vault:
    def __init__(self, path: Path, password: str, *, create: bool = False):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._password = password
        self._lock = FileLock(str(self.path) + ".lock", timeout=0)
        self._held = False
        self._connection: sqlite3.Connection | None = None
        self._salt: bytes | None = None
        self._key: bytes | None = None
        if not password or (create and len(password) < 12):
            raise ValueError("A new vault requires a passphrase of at least 12 characters")
        try:
            self._lock.acquire(timeout=0)
            self._held = True
        except Timeout as exc:
            raise VaultError("This vault is currently open in another application") from exc
        try:
            self._connection = sqlite3.connect(":memory:")
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys=ON")
            if create:
                if self.path.exists():
                    raise VaultError("Vault already exists; refusing to overwrite it")
                self._salt = os.urandom(SALT_SIZE)
                self._key = self._derive(password, self._salt)
                self._connection.execute("PRAGMA user_version=1")
                self._persist()
            else:
                self._load()
        except Exception:
            self.close()
            raise

    @staticmethod
    def _derive(password: str, salt: bytes) -> bytes:
        return hash_secret_raw(password.encode("utf-8"), salt, time_cost=KDF_TIME,
                               memory_cost=KDF_MEMORY_KIB, parallelism=KDF_PARALLELISM,
                               hash_len=32, type=Type.ID)

    @property
    def db(self) -> sqlite3.Connection:
        if self._connection is None:
            raise VaultError("Vault is closed")
        return self._connection

    def _load(self) -> None:
        if not self.path.is_file():
            raise VaultError("Vault file does not exist")
        blob = self.path.read_bytes()
        header = len(MAGIC) + SALT_SIZE + NONCE_SIZE
        if not blob.startswith(MAGIC) or len(blob) < header + 16:
            raise VaultAuthenticationError("Unable to unlock vault")
        self._salt = blob[len(MAGIC):len(MAGIC) + SALT_SIZE]
        nonce = blob[len(MAGIC) + SALT_SIZE:header]
        self._key = self._derive(self._password, self._salt)
        try:
            plain = AESGCM(self._key).decrypt(nonce, blob[header:], MAGIC + self._salt)
            if not plain.startswith(b"SQLite format 3\x00"):
                raise VaultAuthenticationError("Invalid decrypted database")
            self.db.deserialize(plain)
            self.db.execute("PRAGMA foreign_keys=ON")
            result = self.db.execute("PRAGMA quick_check").fetchone()
            if result[0] != "ok":
                raise VaultAuthenticationError("Database integrity check failed")
        except (InvalidTag, sqlite3.DatabaseError, ValueError) as exc:
            raise VaultAuthenticationError("Unable to unlock vault") from exc

    def _persist(self) -> None:
        assert self._key is not None and self._salt is not None
        plain = self.db.serialize()
        nonce = os.urandom(NONCE_SIZE)
        cipher = AESGCM(self._key).encrypt(nonce, plain, MAGIC + self._salt)
        data = MAGIC + self._salt + nonce + cipher
        fd, path = tempfile.mkstemp(prefix=".vault-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(path, self.path)
            if os.name == "posix":
                os.chmod(self.path, 0o600)
                directory_fd = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.db
        if conn.in_transaction:
            raise VaultError("Nested transactions are not supported")
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.commit()
            self._persist()
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            else:
                # If encryption or atomic persistence failed AFTER commit,
                # keep no writable in-memory state that diverges from disk.
                self.close()
            raise

    def verify_passphrase(self, candidate: str) -> bool:
        """Re-authentication against the currently unlocked vault key; never logs input."""
        if self._key is None or self._salt is None or not candidate:
            return False
        other = self._derive(candidate, self._salt)
        return hmac.compare_digest(self._key, other)

    def backup(self, dest: Path) -> Path:
        dest = Path(dest).expanduser().resolve()
        if dest == self.path:
            raise VaultError("Backup destination must differ from source")
        if dest.exists():
            raise VaultError("Backup already exists; refusing overwrite")
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Fully committed vault bytes are already encrypted.
        with dest.open("xb") as f:
            f.write(self.path.read_bytes())
            f.flush()
            os.fsync(f.fileno())
        if os.name == "posix":
            os.chmod(dest, 0o600)
        return dest

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._held:
            self._lock.release()
            self._held = False
        self._password = ""
        self._key = None

    def __enter__(self) -> Vault:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
