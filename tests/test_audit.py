"""Append-only event record."""

from desalplant.audit import summary
from desalplant.audit.event import Event
from desalplant.audit.query import event_at, latest_sequence, list_events
from desalplant.audit.recorder import Recorder
from desalplant.clock import LogicalClock
from desalplant.store.store import Store


def test_event_projects_and_rebuilds():
    event = Event(sequence=1, kind="start", detail="line started", tick=3, id="e1")
    row = event.to_dict()
    assert row == {
        "id": "e1",
        "sequence": 1,
        "kind": "start",
        "detail": "line started",
        "tick": 3,
    }
    assert Event.from_dict(row) == event


def test_recorder_appends_in_order_and_stamps_the_tick():
    store = Store()
    clock = LogicalClock()
    recorder = Recorder(store, clock)
    first = recorder.log("start", "line started")
    clock.advance(4)
    second = recorder.log("produce", "permeate produced")
    assert recorder.sequence == 2
    assert recorder.count() == 2
    assert first.tick == 0
    assert second.tick == 4
    assert recorder.events()[0].sequence == 2
    assert len(recorder.events(1)) == 1
    assert recorder.latest("start").detail == "line started"
    assert recorder.latest("missing") is None


def test_empty_event_kind_is_refused():
    import pytest

    recorder = Recorder(Store())
    with pytest.raises(ValueError):
        recorder.log("", "detail")


def test_recorder_resumes_from_the_sequence_key():
    store = Store()
    Recorder(store).log("start", "line started")
    resumed = Recorder(store)
    assert resumed.sequence == 1


def test_query_reads_the_expected_rows():
    store = Store()
    recorder = Recorder(store)
    recorder.log("start", "line started")
    recorder.log("switch", "tank switched")
    assert event_at(store, 1).kind == "start"
    assert event_at(store, 99) is None
    newest = list_events(store, 2)
    assert [event.kind for event in newest] == ["switch", "start"]
    assert len(list_events(store, 2, 1)) == 1
    assert list_events(store, 0) == ()
    assert latest_sequence(store, "switch") == 2
    assert latest_sequence(store, "missing") == 0


def test_summary_counts_and_filters_by_kind():
    store = Store()
    recorder = Recorder(store)
    recorder.log("start", "one")
    recorder.log("switch", "two")
    recorder.log("start", "three")
    assert summary.counts(store, 3) == {"start": 2, "switch": 1}
    assert summary.total(store, 3) == 3
    recent = summary.recent(store, 3, "start", 1)
    assert len(recent) == 1
    assert recent[0].detail == "three"
    assert summary.recent(store, 3, "start", 0) == ()
