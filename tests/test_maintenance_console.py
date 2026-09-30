"""Console surface for the unified maintenance ledger."""

from support import call, ok, refused


def test_maintenance_routes_are_registered(console):
    routes = console.routes()
    for method, path in (
        ("GET", "/api/maintenance/ledger"),
        ("GET", "/api/maintenance/queue"),
        ("POST", "/api/maintenance/sweep"),
        ("POST", "/api/maintenance/start"),
        ("POST", "/api/maintenance/complete"),
        ("POST", "/api/maintenance/postpone"),
        ("POST", "/api/maintenance/skip"),
    ):
        assert (method, path) in routes


def test_ledger_lists_each_family_with_its_fixed_policy(console):
    body = ok(console, "GET", "/api/maintenance/ledger")
    assert body["running"] is False
    policies = {task["task_id"]: task for task in body["tasks"]}
    assert set(policies) == {"screen-rinse", "media-backwash", "dose-check"}
    rinse = policies["screen-rinse"]
    assert rinse["label"] == "格栅冲洗"
    assert rinse["window"] == "running"
    assert rinse["preemptive"] is True
    assert policies["media-backwash"]["window"] == "stopped"
    assert policies["dose-check"]["window"] == "stopped"


def test_ledger_is_virtual_until_first_decision(console, store):
    # Reading the ledger must not persist anything.
    assert store.count() == 0
    ok(console, "GET", "/api/maintenance/ledger")
    assert store.count() == 0


def test_reminder_then_running_skip_postpone_audit_trail(console, plant):
    plant.clock.advance(100)
    sweep = ok(console, "POST", "/api/maintenance/sweep")
    assert [t["task_id"] for t in sweep["reminders"]] == ["screen-rinse"]

    # Line runs: the screen rinse (running-safe) starts; stopped tasks do not.
    ok(console, "POST", "/api/start")
    plant.clock.advance(200)
    sweep = ok(console, "POST", "/api/maintenance/sweep")
    started = {d["task_id"]: d for d in sweep["started"]}
    postponed = {d["task_id"]: d for d in sweep["postponed"]}
    assert "screen-rinse" in started
    assert "media-backwash" in postponed
    assert "停机窗口" in postponed["media-backwash"]["reason"]

    ledger = ok(console, "GET", "/api/maintenance/ledger")
    backwash = next(t for t in ledger["tasks"] if t["task_id"] == "media-backwash")
    assert backwash["postponed"] is True
    assert backwash["history"][-1]["action"] == "postpone"
    assert backwash["history"][-1]["reason"]
    rinse = next(t for t in ledger["tasks"] if t["task_id"] == "screen-rinse")
    assert rinse["state"] == "active"

    events = ok(console, "GET", "/api/events?limit=50")["events"]
    kinds = {event["kind"] for event in events}
    assert "maintenance/reminder" in kinds
    assert "maintenance/postpone" in kinds
    assert "maintenance/start" in kinds


def test_duplicate_postpone_request_is_idempotent(console, plant):
    plant.clock.advance(300)
    payload = {"task_id": "media-backwash", "reason": "等待停机窗口"}
    first = ok(console, "POST", "/api/maintenance/postpone", payload)
    second = ok(console, "POST", "/api/maintenance/postpone", payload)
    assert first["next_due"] == second["next_due"] == 330
    assert second["idempotent"] is True
    count = ok(console, "GET", "/api/events")["count"]
    ok(console, "POST", "/api/maintenance/postpone", payload)
    assert ok(console, "GET", "/api/events")["count"] == count


def test_stop_window_starts_postponed_tasks_and_completion_reschedules(console, plant):
    # Manually postpone the backwash (reason recorded) while the line is idle
    # but a shutdown window is not being taken yet, then open the window.
    plant.clock.advance(300)
    moved = ok(
        console,
        "POST",
        "/api/maintenance/postpone",
        {"task_id": "media-backwash", "reason": "等待停机窗口"},
    )
    target = moved["next_due"]
    plant.clock.advance(target - 300)
    # The overdue queue drains earliest-due first; walk it to the backwash.
    order = []
    for _ in range(3):
        sweep = ok(console, "POST", "/api/maintenance/sweep")
        if not sweep["started"]:
            break
        head = sweep["started"][0]["task_id"]
        order.append(head)
        ok(console, "POST", "/api/maintenance/complete", {"task_id": head})
    assert "media-backwash" in order
    ledger = ok(console, "GET", "/api/maintenance/ledger")
    backwash = next(t for t in ledger["tasks"] if t["task_id"] == "media-backwash")
    assert backwash["state"] == "pending"
    assert backwash["due_at"] > target


def test_manual_skip_endpoint(console, plant):
    plant.clock.advance(240)
    body = ok(
        console,
        "POST",
        "/api/maintenance/skip",
        {"task_id": "dose-check", "reason": "人工校验已线下完成", "reschedule": False},
    )
    assert body["outcome"] == "skipped"
    ledger = ok(console, "GET", "/api/maintenance/ledger")
    dose = next(t for t in ledger["tasks"] if t["task_id"] == "dose-check")
    assert dose["history"][-1]["action"] == "skip"
    assert dose["history"][-1]["reason"] == "人工校验已线下完成"


def test_unknown_task_is_404_and_empty_reason_is_refused(console, plant):
    plant.clock.advance(300)
    missing = refused(
        console, "POST", "/api/maintenance/start", {"task_id": "nope"}
    )
    assert missing.status == 404
    bad = refused(
        console,
        "POST",
        "/api/maintenance/postpone",
        {"task_id": "media-backwash", "reason": "  "},
    )
    assert bad.status == 400


def test_queue_endpoint_shows_only_window_ready_tasks(console, plant):
    plant.clock.advance(300)
    ok(console, "POST", "/api/start")
    queue = ok(console, "GET", "/api/maintenance/queue")
    # Running: stopped-window tasks are not startable; no rinse is due either.
    assert all(task["window"] == "running" for task in queue["queue"])
