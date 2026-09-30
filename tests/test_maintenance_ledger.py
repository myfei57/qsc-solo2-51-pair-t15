"""Persisted maintenance ledger entries."""

import pytest

from desalplant.maintenance.ledger import Ledger, LedgerEntry
from desalplant.store.store import Store


def make_entry(**overrides) -> LedgerEntry:
    values = dict(
        task_id="media-backwash",
        label="反洗",
        interval=300,
        lead=40,
        priority=2,
        created_at=0,
        base_due=300,
        due_at=300,
    )
    values.update(overrides)
    return LedgerEntry(**values)


def test_due_and_reminder_windows():
    entry = make_entry()
    assert entry.is_due(299) is False
    assert entry.is_due(300) is True
    assert entry.is_due(301) is True
    assert entry.remind_at() == 260
    assert entry.is_reminder_due(259) is False
    assert entry.is_reminder_due(260) is True
    entry.mark_reminded()
    assert entry.is_reminder_due(400) is False


def test_postpone_moves_the_instance_and_keeps_the_base():
    entry = make_entry()
    entry.apply_postpone(330, "设备运行中", "tok@300", at=300)
    assert entry.base_due == 300
    assert entry.due_at == 330
    assert entry.postponements == 1
    assert entry.postponed is True
    assert entry.last_postpone_token == "tok@300"
    assert entry.history[-1]["action"] == "postpone"
    assert entry.history[-1]["reason"] == "设备运行中"
    # The postponed instance (new due 330, lead 40) reminds again from 290.
    assert entry.is_reminder_due(289) is False
    assert entry.is_reminder_due(290) is True


def test_complete_reschedules_the_next_instance():
    entry = make_entry()
    entry.activate(300)
    assert entry.active is True
    next_due = entry.complete(305)
    assert next_due == 605
    assert entry.state == "pending"
    assert entry.base_due == 605
    assert entry.due_at == 605
    assert entry.completed_count == 1
    assert entry.last_completed_at == 305
    assert entry.postponements == 0
    assert entry.history[-1]["action"] == "complete"


def test_active_entry_is_not_due_and_cannot_be_reminded():
    entry = make_entry()
    entry.activate(299)
    assert entry.is_due(500) is False
    assert entry.is_reminder_due(500) is False


def test_entry_round_trips_through_the_store(store):
    ledger = Ledger(store)
    registered = ledger.register("dose-check", "加药", 240, 30, 3, now=0)
    registered.apply_postpone(270, "等待停机窗口", "tok@240", at=240)
    ledger.save(registered)

    reopened = Ledger(Store(store.path))
    loaded = reopened.require("dose-check")
    assert loaded.task_id == "dose-check"
    assert loaded.due_at == 270
    assert loaded.base_due == 240
    assert loaded.postponements == 1
    assert loaded.history[-1]["reason"] == "等待停机窗口"


def test_register_is_idempotent(store):
    ledger = Ledger(store)
    first = ledger.register("dose-check", "加药", 240, 30, 3, now=0)
    second = ledger.register("dose-check", "加药", 240, 30, 3, now=0)
    assert first is not second
    assert second.base_due == first.base_due
    assert len(ledger.list()) == 1
    with pytest.raises(KeyError):
        ledger.require("missing")
