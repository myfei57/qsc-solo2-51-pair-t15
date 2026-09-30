"""Turns the ledger into a priority-ordered maintenance plan.

The planner is the only component that decides *when* and *in what order*
maintenance happens:

* :meth:`Planner.reminders` raises the advance reminder of every instance once.
* :meth:`Planner.queue` orders tasks that are due by ``(due tick, priority,
  id)``, so tasks that fell due together keep a deterministic sequence.
* :meth:`Planner.sweep` tries the queue in order.  A task that cannot start --
  the line is running while it needs a shutdown window, or higher-priority work
  is already in progress -- is skipped with an explicit reason and postponed.
  A task marked active is never touched.
* :meth:`Planner.postpone` is idempotent: postponing the same due instance for
  the same reason twice returns the first decision without a second event.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from ..audit.recorder import Recorder
from ..clock import LogicalClock
from .catalog import Catalog, TaskDef
from .ledger import DEFAULT_SLIP, Ledger, LedgerEntry


@dataclass(frozen=True)
class PlannedTask:
    """One due task together with the reason it may or may not start."""

    task_id: str
    label: str
    priority: int
    base_due: int
    due_at: int
    postponed: bool
    postponements: int
    window: str
    preemptive: bool
    blocked: bool
    block_reason: str
    block_cause: str
    overdue: int

    def to_dict(self, now: int) -> dict[str, Any]:
        """JSON-friendly projection used by the console."""
        return {
            "task_id": self.task_id,
            "label": self.label,
            "priority": self.priority,
            "base_due": self.base_due,
            "due_at": self.due_at,
            "overdue": max(0, now - self.due_at),
            "postponed": self.postponed,
            "postponements": self.postponements,
            "window": self.window,
            "preemptive": self.preemptive,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "block_cause": self.block_cause,
        }


@dataclass(frozen=True)
class Decision:
    """The outcome of attempting one due task."""

    task_id: str
    outcome: str
    reason: str
    due_at: int = 0
    next_due: int = 0
    idempotent: bool = False

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly projection."""
        row = {
            "task_id": self.task_id,
            "outcome": self.outcome,
            "reason": self.reason,
        }
        if self.due_at:
            row["due_at"] = self.due_at
        if self.next_due:
            row["next_due"] = self.next_due
        if self.idempotent:
            row["idempotent"] = True
        return row


@dataclass
class SweepResult:
    """Everything one planning sweep changed."""

    reminders: list[PlannedTask] = field(default_factory=list)
    started: list[Decision] = field(default_factory=list)
    waiting: list[Decision] = field(default_factory=list)
    postponed: list[Decision] = field(default_factory=list)

    def to_dict(self, now: int) -> dict[str, Any]:
        """JSON-friendly projection."""
        return {
            "reminders": [task.to_dict(now) for task in self.reminders],
            "started": [decision.to_dict() for decision in self.started],
            "waiting": [decision.to_dict() for decision in self.waiting],
            "postponed": [decision.to_dict() for decision in self.postponed],
        }


RunningCheck = Callable[[], bool]

# Structured reasons the console and sweep branch on without parsing text.
CAUSE_RUNNING = "line_running"
CAUSE_BUSY = "task_in_progress"


def _running_reason(task: TaskDef) -> tuple[str, str]:
    return (
        CAUSE_RUNNING,
        f"{task.label} 需要停机窗口，设备正在运行，顺延至下一停机窗口",
    )


def _busy_reason(task: TaskDef, active: LedgerEntry) -> tuple[str, str]:
    return (
        CAUSE_BUSY,
        f"{active.label} 正在执行，不可打断；{task.label} 排在其后等待",
    )


class Planner:
    """Orders due maintenance and records every skip or postpone."""

    def __init__(
        self,
        ledger: Ledger,
        catalog: Catalog,
        clock: LogicalClock,
        recorder: Recorder,
        is_running: RunningCheck,
    ) -> None:
        self._ledger = ledger
        self._catalog = catalog
        self._clock = clock
        self._recorder = recorder
        self._is_running = is_running

    # ------------------------------------------------------------- planning

    def plan(self, now: int | None = None) -> list[PlannedTask]:
        """Due tasks in execution order with their blocking reasons.

        Ordering is first-instance-first ``(due tick, priority, id)``; the only
        reordering is a fixed, task-type-based one: a preemptive task type may
        move ahead of *queued* work.  A task already running is never passed.
        """
        at = self._clock.tick if now is None else now
        running = self._is_running()
        active = self._active_entry()
        planned: list[PlannedTask] = []
        for entry in self._due_entries(at):
            definition = self._catalog.get(entry.task_id)
            reason = self._block_reason(definition, entry, running, active)
            planned.append(self._project(definition, entry, reason, at))
        planned.sort(key=lambda task: (task.due_at, task.priority, task.task_id))
        self._apply_precedence(planned, active)
        return planned

    def queue(self, now: int | None = None) -> list[PlannedTask]:
        """Due tasks the current window could start, in execution order."""
        return [task for task in self.plan(now) if not task.blocked]

    def upcoming(self, now: int | None = None) -> list[PlannedTask]:
        """Every registered task, due first then soonest first."""
        at = self._clock.tick if now is None else now
        running = self._is_running()
        active = self._active_entry()
        projected: list[PlannedTask] = []
        for entry in self._entries():
            if entry.active:
                continue
            definition = self._catalog.get(entry.task_id)
            reason = self._block_reason(definition, entry, running, active)
            projected.append(self._project(definition, entry, reason, at))
        projected.sort(key=lambda task: (task.due_at, task.priority, task.task_id))
        self._apply_precedence(projected, active)
        return projected

    def reminders(self, now: int | None = None) -> list[PlannedTask]:
        """Advance reminders that are due, each instance firing exactly once."""
        at = self._clock.tick if now is None else now
        fired: list[PlannedTask] = []
        with self._ledger.lock():
            for entry in self._entries():
                if entry.active or not entry.is_reminder_due(at):
                    continue
                definition = self._catalog.get(entry.task_id)
                entry.mark_reminded()
                self._ledger.save(entry)
                self._recorder.log(
                    "maintenance/reminder",
                    f"{definition.label} 将于 tick {entry.due_at} 到期"
                    f"(提前 {definition.lead} tick 提醒, priority {definition.priority})",
                )
                fired.append(self._project(definition, entry, ("", ""), at))
        fired.sort(key=lambda task: (task.due_at, task.priority, task.task_id))
        return fired

    def sweep(self, now: int | None = None, slip: int = DEFAULT_SLIP) -> SweepResult:
        """Raise reminders, then resolve the due queue in order.

        Tasks blocked by a running line are skipped with a written reason and
        postponed; tasks waiting on work already in progress keep their place.
        Only the single head of the now-startable queue is started per sweep --
        maintenance is serial, so the rest wait for the next sweep after the
        head completes.
        """
        at = self._clock.tick if now is None else now
        result = SweepResult()
        result.reminders = self.reminders(at)
        head_started = False
        for task in self.plan(at):
            entry = self._require_entry(task.task_id)
            if entry.active or not entry.is_due(at):
                continue
            if task.blocked:
                if task.block_cause == CAUSE_RUNNING:
                    # Equipment is running while the task needs a stop window:
                    # record the skip with its reason and postpone.
                    result.postponed.append(
                        self.postpone(task.task_id, task.block_reason, slip=slip, now=at)
                    )
                else:
                    # Another task is in progress.  Do not skip or postpone:
                    # the instance keeps its place in the time sequence.
                    result.waiting.append(
                        Decision(task.task_id, "waiting", task.block_reason, task.due_at)
                    )
            elif head_started:
                # The window only runs one task at a time.
                result.waiting.append(
                    Decision(
                        task.task_id,
                        "waiting",
                        f"排在队列中，等待前序维护完成",
                        task.due_at,
                    )
                )
            else:
                result.started.append(self.start(task.task_id, now=at))
                head_started = True
        return result

    # ------------------------------------------------------------ mutation

    def start(self, task_id: str, now: int | None = None) -> Decision:
        """Start a due task, refusing when its fixed policy blocks it."""
        at = self._clock.tick if now is None else now
        definition = self._catalog.get(task_id)
        with self._ledger.lock():
            entry = self._require_entry(task_id)
            if entry.active:
                return Decision(task_id, "active", f"{definition.label} 已在执行中")
            if not entry.is_due(at):
                return Decision(
                    task_id, "waiting", f"{definition.label} 尚未到期", next_due=entry.due_at
                )
            running = self._is_running()
            active = self._active_entry()
            _, reason = self._block_reason(definition, entry, running, active)
            if reason:
                return Decision(
                    task_id, "blocked", reason, due_at=entry.due_at
                )
            entry.activate(at)
            self._ledger.save(entry)
            self._recorder.log(
                "maintenance/start",
                f"{definition.label} 开始执行 (到期 tick {entry.due_at})",
            )
            return Decision(task_id, "started", f"{definition.label} 开始执行", entry.due_at)

    def complete(self, task_id: str, now: int | None = None) -> Decision:
        """Finish an active task and reschedule its next instance."""
        at = self._clock.tick if now is None else now
        definition = self._catalog.get(task_id)
        with self._ledger.lock():
            entry = self._require_entry(task_id)
            if not entry.active:
                return Decision(task_id, "idle", f"{definition.label} 未在执行，无需完成")
            done_due = entry.due_at
            next_due = entry.complete(at)
            self._ledger.save(entry)
            self._recorder.log(
                "maintenance/complete",
                f"{definition.label} 完成，下次到期 tick {next_due}",
            )
            return Decision(
                task_id, "completed", f"{definition.label} 完成", done_due, next_due
            )

    def postpone(
        self,
        task_id: str,
        reason: str,
        slip: int = DEFAULT_SLIP,
        now: int | None = None,
    ) -> Decision:
        """Skip a due instance with ``reason`` and postpone it once.

        Calling this twice for the same instance and reason is idempotent:
        the second call reports the first decision and neither writes a new
        audit event nor moves the due tick a second time.
        """
        if not reason or not reason.strip():
            raise ValueError("postpone reason must not be empty")
        if slip < 1:
            raise ValueError("postpone slip must be positive")
        at = self._clock.tick if now is None else now
        definition = self._catalog.get(task_id)
        with self._ledger.lock():
            entry = self._require_entry(task_id)
            if entry.active:
                # Work in progress cannot be interrupted, so it cannot be
                # postponed either; it must be completed or skipped by hand.
                return Decision(
                    task_id,
                    "active",
                    f"{definition.label} 正在执行，不可顺延",
                    entry.due_at,
                )
            # An instance is postponed at most once.  Any repeat -- the same
            # reason, a different reason, a later tick or a racing duplicate --
            # reports the first decision and never writes a second event.
            if entry.postponed_instance:
                return Decision(
                    task_id,
                    "postponed",
                    f"{definition.label} 已顺延一次，忽略重复顺延请求",
                    entry.base_due,
                    entry.due_at,
                    idempotent=True,
                )
            token = self._token(task_id, entry.base_due, reason)
            until = entry.due_at + slip
            entry.apply_postpone(until, reason, token, at)
            self._ledger.save(entry)
            self._recorder.log(
                "maintenance/postpone",
                f"{definition.label} 跳过本次到期(tick {entry.base_due})：{reason}；"
                f"顺延至 tick {until}",
            )
            return Decision(
                task_id,
                "postponed",
                reason,
                entry.base_due,
                until,
            )

    def skip(
        self,
        task_id: str,
        reason: str,
        reschedule: bool = True,
        slip: int = DEFAULT_SLIP,
        now: int | None = None,
    ) -> Decision:
        """Manually skip a due instance, recording why.

        With ``reschedule`` the instance is also postponed; otherwise the task
        is acknowledged as skipped but stays due so the console keeps showing
        it as overdue.
        """
        if not reason or not reason.strip():
            raise ValueError("skip reason must not be empty")
        at = self._clock.tick if now is None else now
        definition = self._catalog.get(task_id)
        with self._ledger.lock():
            entry = self._require_entry(task_id)
            if entry.active:
                return Decision(task_id, "active", f"{definition.label} 正在执行，不可跳过")
            until = entry.due_at + slip if reschedule else None
            skipped_due = entry.due_at
            entry.apply_skip(reason, at, until)
            if until is not None:
                # Manual reschedule consumes the instance's one postponement.
                entry.postponed_instance = True
            self._ledger.save(entry)
            if until is not None:
                detail = (
                    f"{definition.label} 人工跳过本次到期(tick {skipped_due}): {reason}"
                    f"；顺延至 tick {until}"
                )
            else:
                detail = f"{definition.label} 人工跳过(tick {skipped_due}): {reason}"
            self._recorder.log("maintenance/skip", detail)
            return Decision(
                task_id,
                "skipped",
                reason,
                skipped_due,
                until or 0,
            )

    # ------------------------------------------------------------- helpers

    def active_entry(self) -> LedgerEntry | None:
        """The task currently in progress, if any."""
        for entry in self._entries():
            if entry.active:
                return entry
        return None

    def entry_for(self, task_id: str) -> LedgerEntry:
        """Stored entry or the virtual catalogue default for a task."""
        entry = self._ledger.find(task_id)
        if entry is not None:
            return entry
        return self._virtual_entry(self._catalog.get(task_id))

    def _active_entry(self) -> LedgerEntry | None:
        return self.active_entry()

    def _due_entries(self, now: int) -> tuple[LedgerEntry, ...]:
        return tuple(entry for entry in self._entries() if entry.is_due(now))

    def _virtual_entry(self, definition: TaskDef) -> LedgerEntry:
        # First instance is anchored at tick 0 + interval, independent of when
        # the entry is first persisted, so materialisation never moves a date.
        task_id = str(definition.type)
        return LedgerEntry(
            task_id=task_id,
            label=definition.label,
            interval=definition.interval,
            lead=definition.lead,
            priority=definition.priority,
            created_at=0,
            base_due=definition.interval,
            due_at=definition.interval,
        )

    def _entries(self) -> tuple[LedgerEntry, ...]:
        """Stored entries merged with not-yet-persisted catalogue defaults."""
        stored = {entry.task_id: entry for entry in self._ledger.list()}
        merged: list[LedgerEntry] = []
        for definition in self._catalog.types():
            task_id = str(definition.type)
            entry = stored.get(task_id)
            if entry is None:
                # Visible on the ledger but not persisted until something about
                # it actually changes.
                entry = self._virtual_entry(definition)
            merged.append(entry)
        return tuple(merged)

    def _require_entry(self, task_id: str) -> LedgerEntry:
        """Entry for a catalogue task, persisting the default on first touch."""
        entry = self._ledger.find(task_id)
        if entry is None:
            definition = self._catalog.get(task_id)
            entry = self._virtual_entry(definition)
            entry.created_at = self._clock.tick
            self._ledger.save(entry)
        return entry

    def _block_reason(
        self,
        definition: TaskDef,
        entry: LedgerEntry,
        running: bool,
        active: LedgerEntry | None,
    ) -> tuple[str, str]:
        """Return ``(cause, human reason)``; empty strings when startable."""
        if entry.active:
            return "", ""
        if definition.policy.requires_stop and running:
            return _running_reason(definition)
        if active is not None and active.task_id != entry.task_id:
            # A task already in progress runs to completion: preemption only
            # reorders tasks still queued, it never interrupts active work.
            return _busy_reason(definition, active)
        return "", ""

    def _project(
        self,
        definition: TaskDef,
        entry: LedgerEntry,
        block: tuple[str, str],
        now: int,
    ) -> PlannedTask:
        cause, reason = block
        return PlannedTask(
            task_id=entry.task_id,
            label=definition.label,
            priority=definition.priority,
            base_due=entry.base_due,
            due_at=entry.due_at,
            postponed=entry.postponed,
            postponements=entry.postponements,
            window=str(definition.policy.window),
            preemptive=definition.policy.preemptive,
            blocked=bool(reason),
            block_reason=reason,
            block_cause=cause,
            overdue=max(0, now - entry.due_at),
        )

    def _apply_precedence(
        self, tasks: list[PlannedTask], active: LedgerEntry | None
    ) -> None:
        """Let a preemptive task type overtake *queued* work.

        Base order is ``(due tick, priority, id)``.  A preemptive task pulls
        ahead of the non-preemptive tasks queued before it -- the fixed,
        type-based answer to "may a high-priority task jump the queue" -- but it
        never passes an active task, which the caller has already excluded.
        """
        if len(tasks) < 2:
            return
        reordered: list[PlannedTask] = []
        for task in tasks:
            if task.preemptive and not task.blocked:
                insert_at = len(reordered)
                while insert_at > 0 and not reordered[insert_at - 1].preemptive:
                    insert_at -= 1
                reordered.insert(insert_at, task)
            else:
                reordered.append(task)
        tasks[:] = reordered

    @staticmethod
    def _token(task_id: str, due_at: int, reason: str) -> str:
        return f"{task_id}@{due_at}:{reason.strip()}"
