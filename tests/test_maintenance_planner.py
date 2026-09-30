"""Priority ordering, shutdown windows, skips and idempotent postponements."""

import threading

import pytest

from desalplant.audit.recorder import Recorder
from desalplant.clock import LogicalClock
from desalplant.maintenance.catalog import Catalog, TaskDef, TaskType
from desalplant.maintenance.ledger import Ledger
from desalplant.maintenance.planner import Planner
from desalplant.maintenance.policy import ExecutionPolicy, WindowRequirement
from desalplant.store.store import Store


class Line:
    """Stand-in for the running flag the planner must consult."""

    def __init__(self, running=False):
        self.running = running

    def is_running(self):
        return self.running


def build(catalog=None, running=False):
    store = Store()
    clock = LogicalClock()
    recorder = Recorder(store, clock)
    ledger = Ledger(store)
    line = Line(running)
    planner = Planner(
        ledger, catalog or Catalog(), clock, recorder, line.is_running
    )
    return planner, ledger, clock, recorder, line


def task_ids(tasks):
    return [task.task_id for task in tasks]


def test_reminders_fire_once_per_instance_ahead_of_due():
    planner, ledger, clock, recorder, _ = build()
    # screen-rinse is due at 120 with lead 20 -> reminder at 100.
    assert task_ids(planner.reminders(99)) == []
    fired = planner.reminders(100)
    assert task_ids(fired) == ["screen-rinse"]
    assert [e.kind for e in recorder.events()] == ["maintenance/reminder"]
    # Same instance never reminds twice.
    assert planner.reminders(110) == []
    assert recorder.count() == 1


def test_queue_orders_same_tick_by_priority_then_id():
    custom = Catalog(
        (
            TaskDef(TaskType.MEDIA_BACKWASH, "反洗", 100, 0, 2,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
            TaskDef(TaskType.DOSE_CHECK, "加药", 100, 0, 3,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
            TaskDef(TaskType.SCREEN_RINSE, "格栅冲洗", 100, 0, 1,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
        )
    )
    planner, _, _, _, _ = build(custom)
    order = task_ids(planner.queue(100))
    assert order == ["screen-rinse", "media-backwash", "dose-check"]


def test_running_line_skips_stopped_window_tasks_with_a_reason_and_postpones():
    planner, ledger, clock, recorder, line = build(running=True)
    # media-backwash due 300; line running.
    result = planner.sweep(300)
    decisions = {d.task_id: d for d in result.postponed}
    assert "media-backwash" in decisions
    decision = decisions["media-backwash"]
    assert decision.outcome == "postponed"
    assert "停机窗口" in decision.reason
    assert decision.next_due == 330
    entry = ledger.require("media-backwash")
    assert entry.due_at == 330
    assert entry.base_due == 300
    assert entry.history[-1]["action"] == "postpone"
    kinds = [e.kind for e in recorder.events()]
    assert "maintenance/postpone" in kinds


def test_running_line_starts_running_safe_tasks():
    planner, ledger, clock, recorder, line = build(running=True)
    result = planner.sweep(120)
    assert [d.task_id for d in result.started] == ["screen-rinse"]
    assert ledger.require("screen-rinse").active is True


def test_shutdown_window_runs_postponed_tasks_after_stop():
    custom = Catalog(
        (
            TaskDef(TaskType.SCREEN_RINSE, "格栅冲洗", 1000, 0, 1,
                    ExecutionPolicy(WindowRequirement.RUNNING, preemptive=True)),
            TaskDef(TaskType.MEDIA_BACKWASH, "反洗", 300, 0, 2,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
            TaskDef(TaskType.DOSE_CHECK, "加药", 300, 0, 3,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
        )
    )
    planner, ledger, clock, recorder, line = build(custom, running=True)
    # Both stopped tasks fall due at 300 while running and postpone together.
    postponed = {d.task_id: d.next_due for d in planner.sweep(300).postponed}
    assert postponed == {"dose-check": 330, "media-backwash": 330}
    line.running = False
    result = planner.sweep(330)
    started = [d.task_id for d in result.started]
    waiting = [d.task_id for d in result.waiting]
    # One task starts per sweep; same tick -> priority order, the rest wait.
    assert started == ["media-backwash"]
    assert waiting == ["dose-check"]
    assert ledger.require("media-backwash").active is True


def test_active_task_is_never_interrupted_even_by_a_higher_priority_due_task():
    # Lower-priority stopped-window task starts first (earlier due), then the
    # preemptive screen rinse falls due while it is still active.
    custom = Catalog(
        (
            TaskDef(TaskType.MEDIA_BACKWASH, "反洗", 100, 0, 2,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
            TaskDef(TaskType.SCREEN_RINSE, "格栅冲洗", 100, 0, 1,
                    ExecutionPolicy(WindowRequirement.RUNNING, preemptive=True)),
        )
    )
    planner, ledger, _, _, line = build(custom, running=False)
    # Same tick due: priority 1 rinse would normally lead.  Force the backwash
    # active first to prove an active task cannot be overtaken afterwards.
    planner.start("media-backwash", now=100)
    plan = task_ids(planner.plan(100))
    assert plan == ["screen-rinse"]
    blocked = planner.plan(100)[0]
    assert blocked.blocked is True
    assert "不可打断" in blocked.block_reason
    # A sweep must not skip/postpone it nor start it: it simply waits.
    result = planner.sweep(100)
    assert result.started == []
    assert result.postponed == []
    waiting = {d.task_id: d for d in result.waiting}
    assert "screen-rinse" in waiting
    assert ledger.require("screen-rinse").due_at == 100
    # Completing the backwash frees the rinse without any state corruption.
    planner.complete("media-backwash", now=101)
    assert [d.task_id for d in planner.sweep(101).started] == ["screen-rinse"]


def test_preemptive_type_overtakes_queued_work_but_never_active_work():
    # Rinse due later (200) than queued stopped tasks (100), line stopped so
    # nothing is running yet: nothing is active until a sweep starts the first.
    custom = Catalog(
        (
            TaskDef(TaskType.SCREEN_RINSE, "格栅冲洗", 200, 0, 1,
                    ExecutionPolicy(WindowRequirement.RUNNING, preemptive=True)),
            TaskDef(TaskType.MEDIA_BACKWASH, "反洗", 100, 0, 2,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
            TaskDef(TaskType.DOSE_CHECK, "加药", 100, 0, 3,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
        )
    )
    planner, _, _, _, line = build(custom, running=False)
    # At tick 100 the rinse is not due, so the stopped tasks keep their order.
    assert task_ids(planner.queue(100)) == ["media-backwash", "dose-check"]
    # At tick 200 all three are overdue; the preemptive rinse jumps the queue.
    assert task_ids(planner.queue(200)) == [
        "screen-rinse",
        "media-backwash",
        "dose-check",
    ]


def test_postpone_is_idempotent_for_the_same_instance_and_reason():
    planner, ledger, clock, recorder, _ = build()
    first = planner.postpone("media-backwash", "设备运行中", now=300)
    second = planner.postpone("media-backwash", "设备运行中", now=300)
    third = planner.postpone("media-backwash", "换了个新原因", now=301)
    assert first.next_due == 330
    assert first.idempotent is False
    # Repeated postponement of the same instance -- same reason, new reason or a
    # later tick -- never postpones a second time.
    assert second.next_due == 330 and second.idempotent is True
    assert third.next_due == 330 and third.idempotent is True
    assert ledger.require("media-backwash").postponements == 1
    assert ledger.require("media-backwash").due_at == 330
    assert recorder.count() == 1


def test_postpone_after_completion_is_a_fresh_instance_not_a_duplicate():
    planner, ledger, _, _, _ = build()
    planner.postpone("media-backwash", "设备运行中", now=300)
    # Completing (the postponed instance) opens a brand-new instance, which may
    # be postponed again even though the previous instance already was.
    planner.start("media-backwash", now=330)
    planner.complete("media-backwash", now=331)  # next due 631
    decision = planner.postpone("media-backwash", "设备运行中", now=631)
    assert decision.idempotent is False
    assert decision.due_at == 631
    assert decision.next_due == 661


def test_manual_skip_records_reason_and_reschedules_or_holds():
    planner, ledger, _, recorder, _ = build()
    held = planner.skip("media-backwash", "人工开盖检修", reschedule=False, now=300)
    assert held.outcome == "skipped"
    assert ledger.require("media-backwash").due_at == 300  # stays overdue
    moved = planner.skip("media-backwash", "备件未到", reschedule=True, now=300)
    assert moved.next_due == 330
    assert ledger.require("media-backwash").due_at == 330
    kinds = [e.kind for e in recorder.events()]
    assert kinds == ["maintenance/skip", "maintenance/skip"]


def test_active_task_cannot_be_postponed_or_skipped():
    planner, _, _, _, _ = build()
    planner.start("screen-rinse", now=120)
    assert planner.postpone("screen-rinse", "try", now=120).outcome == "active"
    assert planner.skip("screen-rinse", "try", now=120).outcome == "active"


def test_start_before_due_waits_and_unknown_task_is_rejected():
    planner, _, _, _, _ = build()
    assert planner.start("screen-rinse", now=10).outcome == "waiting"
    with pytest.raises(KeyError):
        planner.start("nope", now=120)


def test_concurrent_postponements_apply_exactly_once():
    planner, ledger, _, recorder, _ = build()
    barrier = threading.Barrier(8)
    outcomes = []

    def worker():
        barrier.wait()
        outcomes.append(planner.postpone("media-backwash", "设备运行中", now=300))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    applied = [d for d in outcomes if not d.idempotent]
    duplicates = [d for d in outcomes if d.idempotent]
    assert len(applied) == 1
    assert len(duplicates) == 7
    assert {d.next_due for d in outcomes} == {330}
    assert ledger.require("media-backwash").postponements == 1
    assert ledger.require("media-backwash").due_at == 330
    assert recorder.count() == 1


def test_every_decision_is_on_the_audit_record():
    custom = Catalog(
        (
            TaskDef(TaskType.SCREEN_RINSE, "格栅冲洗", 1000, 0, 1,
                    ExecutionPolicy(WindowRequirement.RUNNING, preemptive=True)),
            TaskDef(TaskType.MEDIA_BACKWASH, "反洗", 300, 0, 2,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
            TaskDef(TaskType.DOSE_CHECK, "加药", 600, 0, 3,
                    ExecutionPolicy(WindowRequirement.STOPPED)),
        )
    )
    planner, _, _, recorder, line = build(custom, running=True)
    planner.reminders(990)
    assert "maintenance/reminder" in {e.kind for e in recorder.events()}
    planner.sweep(300)  # backwash postponed
    assert "maintenance/postpone" in {e.kind for e in recorder.events()}
    line.running = False
    started = planner.sweep(330).started
    assert [d.task_id for d in started] == ["media-backwash"]
    planner.complete("media-backwash", now=331)
    kinds = {event.kind for event in recorder.events()}
    assert "maintenance/start" in kinds
    assert "maintenance/complete" in kinds
