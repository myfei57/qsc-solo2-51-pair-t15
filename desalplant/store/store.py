"""File-backed key space with atomic flushes.

The store keeps the whole document in memory and rewrites it through a temporary
file, so a crash mid-write never leaves a half-written document behind. Reads
never create the file, which keeps a first run side-effect free.
"""

import os
import threading
from typing import Any

from ..errors import StoreError, UnknownKeyError
from . import snapshot as snapshot_module
from .checksum import digest
from .codec import decode, encode
from .query import select


class Store:
    """A small persisted mapping used as the service's source of truth."""

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {}
        self.load()

    @property
    def path(self) -> str | None:
        """Location of the persisted document, if any."""
        return self._path

    def load(self) -> None:
        """Read the document from disk; a missing file leaves the store empty."""
        if self._path is None or not os.path.exists(self._path):
            return
        with open(self._path, "r", encoding="utf-8") as handle:
            text = handle.read()
        if not text.strip():
            return
        document = decode(text)
        if not isinstance(document, dict):
            raise StoreError("persisted document is not an object")
        self._data = dict(document)

    def put(self, key: str, value: Any) -> None:
        """Write a key and flush the document."""
        if not key:
            raise StoreError("key must not be empty")
        with self._lock:
            self._data[key] = value
            self.flush()

    def get(self, key: str, default: Any = None) -> Any:
        """Read a key, returning ``default`` when it was never written."""
        with self._lock:
            return self._data.get(key, default)

    def require(self, key: str) -> Any:
        """Read a key, raising when it was never written."""
        with self._lock:
            if key not in self._data:
                raise UnknownKeyError(f"no stored value for {key}")
            return self._data[key]

    def has(self, key: str) -> bool:
        """Whether a key holds a value."""
        with self._lock:
            return key in self._data

    def keys(self, prefix: str = "") -> tuple[str, ...]:
        """Sorted keys under a prefix."""
        with self._lock:
            return select(self._data.keys(), prefix)

    def count(self) -> int:
        """Number of stored keys."""
        with self._lock:
            return len(self._data)

    def export(self) -> dict[str, Any]:
        """A detached copy of the whole mapping."""
        with self._lock:
            return dict(self._data)

    def checksum(self) -> str:
        """Digest of the current content."""
        with self._lock:
            return digest(self._data)

    def verify(self, checksum: str) -> bool:
        """Whether ``checksum`` still describes the current content."""
        return self.checksum() == checksum

    def snapshot(self, prefix: str = "") -> snapshot_module.Snapshot:
        """Frozen count, digest and key list."""
        with self._lock:
            return snapshot_module.build(self._data, prefix)

    def flush(self) -> None:
        """Rewrite the document atomically, when a path is configured."""
        if self._path is None:
            return
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary = f"{self._path}.tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                handle.write(encode(self._data))
            os.replace(temporary, self._path)
        except OSError as error:
            raise StoreError(f"could not persist {self._path}: {error}") from error
