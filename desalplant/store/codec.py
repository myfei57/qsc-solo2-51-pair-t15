"""Stable textual encoding used for hashing and persistence."""

import json
from typing import Any


def canonical(value: Any) -> str:
    """Stable textual form of a value, independent of mapping order."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def encode(value: Any) -> str:
    """Pretty textual form used inside the persisted document."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def decode(text: str) -> Any:
    """Inverse of :func:`encode` for a single document."""
    return json.loads(text)
