"""Frozen summary of the persisted key space."""

from dataclasses import dataclass
from typing import Any, Mapping

from .checksum import digest
from .query import select

SNAPSHOT_VERSION = 1


@dataclass(frozen=True)
class Snapshot:
    """Count and digest of the persisted document at one instant."""

    version: int
    count: int
    checksum: str
    keys: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "count": self.count,
            "checksum": self.checksum,
            "keys": list(self.keys),
        }


def build(rows: Mapping[str, Any], prefix: str = "") -> Snapshot:
    """Snapshot a mapping, optionally restricted to a key prefix."""
    keys = select(rows.keys(), prefix)
    restricted = {key: rows[key] for key in keys}
    return Snapshot(
        version=SNAPSHOT_VERSION,
        count=len(restricted),
        checksum=digest(restricted),
        keys=keys,
    )
