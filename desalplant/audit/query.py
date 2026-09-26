"""Read side of the append-only event record."""

from ..store import keys
from ..store.store import Store
from .event import Event


def event_at(store: Store, sequence: int) -> Event | None:
    """Event stored at ``sequence``, or ``None`` when nothing was written."""
    row = store.get(keys.audit_event_key(sequence))
    if row is None:
        return None
    return Event.from_dict(row)


def list_events(store: Store, highest: int, limit: int = 0) -> tuple[Event, ...]:
    """Newest-first events, capped at ``limit`` when it is positive."""
    if highest <= 0:
        return ()
    bound = highest if limit <= 0 else min(limit, highest)
    collected: list[Event] = []
    for sequence in range(highest, highest - bound, -1):
        event = event_at(store, sequence)
        if event is not None:
            collected.append(event)
    return tuple(collected)


def latest_sequence(store: Store, kind: str) -> int:
    """Sequence of the newest event of ``kind``, or zero when there is none."""
    value = store.get(keys.audit_last_key(kind), 0)
    return int(value or 0)
