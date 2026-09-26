"""Content digest of a committed key space."""

import hashlib
from typing import Any, Mapping

from .codec import canonical


def digest(rows: Mapping[str, Any]) -> str:
    """Digest of a mapping, insensitive to insertion order."""
    payload = "".join(f"{key}\x00{canonical(rows[key])}\n" for key in sorted(rows))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def short(digest_value: str, width: int = 12) -> str:
    """Leading slice of a digest, for display in reports."""
    if width < 1:
        raise ValueError("width must be positive")
    return digest_value[:width]
