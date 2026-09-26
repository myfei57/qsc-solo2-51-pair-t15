"""Aggregate views over the event record."""

from ..store.store import Store
from . import query
from .event import Event


def counts(store: Store, highest: int) -> dict[str, int]:
    """Number of events recorded per kind."""
    summary: dict[str, int] = {}
    for event in query.list_events(store, highest):
        summary[event.kind] = summary.get(event.kind, 0) + 1
    return dict(sorted(summary.items()))


def recent(store: Store, highest: int, kind: str, limit: int) -> tuple[Event, ...]:
    """Newest ``limit`` events of a kind."""
    if limit <= 0:
        return ()
    collected: list[Event] = []
    for event in query.list_events(store, highest):
        if event.kind != kind:
            continue
        collected.append(event)
        if len(collected) >= limit:
            break
    return tuple(collected)


def total(store: Store, highest: int) -> int:
    """Number of events recorded so far."""
    return len(query.list_events(store, highest))
