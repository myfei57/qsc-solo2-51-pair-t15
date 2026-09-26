"""Write side of the append-only event record."""

from ..clock import LogicalClock
from ..ns.ids import new_id
from ..store import keys
from ..store.store import Store
from . import query
from .event import Event


class Recorder:
    """Appends events and keeps their running sequence number."""

    def __init__(self, store: Store, clock: LogicalClock | None = None) -> None:
        self._store = store
        self._clock = clock
        self._sequence = int(store.get(keys.AUDIT_SEQUENCE, 0) or 0)

    @property
    def sequence(self) -> int:
        """Sequence number of the newest event."""
        return self._sequence

    def log(self, kind: str, detail: str) -> Event:
        """Append an event and return it."""
        if not kind:
            raise ValueError("event kind must not be empty")
        self._sequence += 1
        tick = self._clock.tick if self._clock is not None else 0
        event = Event(
            sequence=self._sequence,
            kind=kind,
            detail=detail,
            tick=tick,
            id=new_id(),
        )
        self._store.put(keys.AUDIT_SEQUENCE, self._sequence)
        self._store.put(keys.audit_event_key(self._sequence), event.to_dict())
        self._store.put(keys.audit_last_key(kind), self._sequence)
        return event

    def count(self) -> int:
        """Number of events recorded so far."""
        return self._sequence

    def events(self, limit: int = 0) -> tuple[Event, ...]:
        """Newest-first events, capped at ``limit`` when it is positive."""
        return query.list_events(self._store, self._sequence, limit)

    def latest(self, kind: str) -> Event | None:
        """Newest event of a kind, or ``None`` when there is none."""
        sequence = query.latest_sequence(self._store, kind)
        if sequence <= 0:
            return None
        return query.event_at(self._store, sequence)
