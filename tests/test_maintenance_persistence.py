"""Maintenance ledger persistence across service restarts."""

from desalplant.app import build_application
from desalplant.config import Config
from support import ok


def test_postpone_and_audit_survive_a_restart(tmp_path):
    config = Config(data_dir=str(tmp_path / "data"))
    first = build_application(config)
    console = first.console
    first.plant.clock.advance(300)
    payload = {"task_id": "media-backwash", "reason": "等待停机窗口"}
    moved = ok(console, "POST", "/api/maintenance/postpone", payload)
    assert moved["next_due"] == 330

    reopened = build_application(config)
    console = reopened.console
    ledger = ok(console, "GET", "/api/maintenance/ledger")
    backwash = next(t for t in ledger["tasks"] if t["task_id"] == "media-backwash")
    assert backwash["due_at"] == 330
    assert backwash["base_due"] == 300
    assert backwash["postponed"] is True
    assert backwash["history"][-1]["action"] == "postpone"
    assert backwash["history"][-1]["reason"] == "等待停机窗口"

    # The duplicate postpone stays idempotent after the restart as well.
    repeat = ok(console, "POST", "/api/maintenance/postpone", payload)
    assert repeat["idempotent"] is True
    assert repeat["next_due"] == 330
    ledger = ok(console, "GET", "/api/maintenance/ledger")
    backwash = next(t for t in ledger["tasks"] if t["task_id"] == "media-backwash")
    assert backwash["postponements"] == 1
    # Audit events are still there after reopening the store.
    kinds = {e["kind"] for e in ok(console, "GET", "/api/events?limit=50")["events"]}
    assert "maintenance/postpone" in kinds


def test_active_task_cannot_be_acted_on_after_restart(tmp_path):
    config = Config(data_dir=str(tmp_path / "data"))
    first = build_application(config)
    first.plant.clock.advance(120)
    first.plant.maintenance_start("screen-rinse")

    reopened = build_application(config)
    ledger = ok(reopened.console, "GET", "/api/maintenance/ledger")
    rinse = next(t for t in ledger["tasks"] if t["task_id"] == "screen-rinse")
    assert rinse["state"] == "active"
    # Other due tasks see the active rinse and wait rather than overtake it.
    reopened.plant.clock.advance(200)
    queue = ok(reopened.console, "GET", "/api/maintenance/queue")["queue"]
    assert queue == []
