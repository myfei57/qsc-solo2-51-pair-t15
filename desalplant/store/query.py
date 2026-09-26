"""Key selection helpers shared by the store and the audit query layer."""

from typing import Iterable


def matches(key: str, prefix: str) -> bool:
    """True when ``key`` lives under ``prefix``; an empty prefix selects all."""
    if not prefix:
        return True
    return key.startswith(prefix)


def select(keys: Iterable[str], prefix: str) -> tuple[str, ...]:
    """Sorted keys under a prefix, as a stable tuple."""
    return tuple(sorted(key for key in keys if matches(key, prefix)))
