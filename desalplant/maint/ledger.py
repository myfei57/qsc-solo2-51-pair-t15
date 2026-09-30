"""Unified maintenance due ledger.

The ledger lists every recurring chore, sorts the ones due in the same window by
priority then due tick, and decides for each whether it may run or must be
skipped and postponed.  Every skip and postpone is written to the append-only
audit record with its reason, and a postpone is idempotent: repeating it for the
same due cycle returns the original record without moving the deadline twice.
"""

from typing import Iterable

from ..audit.recorder import Recorder
from ..clock import LogicalClock
from ..ns.state import PlantState
from .plan import ACTION_RUN, ACTION_SKIP, MaintAction, MaintPlan
from .postpone import Postponement
from .task import DEFAULT_TASK_TYPES, InterruptPolicy, TaskSchedule, TaskType
from .window import skip_reason, window_available, window_label

DEFAULT_LEAD = 30


class MaintLedger:
    """Due state and resolve pass for the recurring maintenance chores."""

    def __init__(
        self,
        recorder: Recorder,
        clock: LogicalClock,
        task_types: Iterable[TaskType] = DEFAULT_TASK_TYPES,
        lead: int = DEFAULT_LEAD,
    ) -> None:
        if lead < 0:
            raise ValueError("lead must not be negative")
        self._recorder = recorder
        self._clock = clock
        self._lead = lead
        self._tasks: dict[str, TaskSchedule] = {
            task.kind: TaskSchedule(task_type=task) for task in task_types
        }
        self._postponements: dict[tuple[str, int], Postponement] = {}

    # ------------------------------------------------------------- properties

    @property
    def lead(self) -> int:
        """Reminder lead in ticks."""
        return self._lead

    def tick(self) -> int:
        """Current logical tick."""
        return self._clock.tick

    def schedule(self, kind: str) -> TaskSchedule:
        """The schedule for one chore."""
        return self._tasks[kind]

    def kinds(self) -> tuple[str, ...]:
        """Known chore kinds in a stable order."""
        return tuple(sorted(self._tasks))

    # --------------------------------------------------------------- ordering

    def _ordered(self, schedules: Iterable[TaskSchedule]) -> tuple[TaskSchedule, ...]:
        """Sort by priority (high first), then due tick, then kind."""
        return tuple(
            sorted(schedules, key=lambda sched: (-sched.priority, sched.due_at, sched.kind))
        )

    # ------------------------------------------------------------------ views

    def due(self, now: int | None = None) -> tuple[TaskSchedule, ...]:
        """Chores whose due tick has arrived, in priority order."""
        now = self.tick() if now is None else now
        return self._ordered(sched for sched in self._tasks.values() if sched.due(now))

    def upcoming(self, now: int | None = None, lead: int | None = None) -> tuple[TaskSchedule, ...]:
        """Chores due within the reminder window, in priority order."""
        now = self.tick() if now is None else now
        ahead = self._lead if lead is None else lead
        return self._ordered(
            sched
            for sched in self._tasks.values()
            if not sched.due(now) and now + ahead >= sched.due_at
        )

    def deferred(self) -> tuple[TaskSchedule, ...]:
        """Chores carrying an unresolved postponement."""
        return self._ordered(
            sched for sched in self._tasks.values() if sched.deferred_from is not None
        )

    def status(self, now: int | None = None) -> dict:
        """Full ledger view for the console."""
        now = self.tick() if now is None else now
        tasks = []
        for sched in self._ordered(self._tasks.values()):
            if sched.deferred_from is not None:
                state = "deferred"
            elif sched.due(now):
                state = "due"
            elif now + self._lead >= sched.due_at:
                state = "upcoming"
            else:
                state = "ok"
            tasks.append(
                {
                    "kind": sched.kind,
                    "name": sched.task_type.name,
                    "priority": sched.priority,
                    "interrupt": str(sched.interrupt),
                    "interval": sched.task_type.interval,
                    "last_done": sched.last_done,
                    "due_at": sched.due_at,
                    "state": state,
                    "overdue": sched.overdue(now),
                    "deferred_from": sched.deferred_from,
                    "deferred_to": sched.deferred_to,
                }
            )
        return {"tick": now, "lead": self._lead, "tasks": tasks}

    # ------------------------------------------------------------- resolve pass

    def resolve(self, state: PlantState, now: int | None = None) -> MaintPlan:
        """Decide run vs skip for every due chore and record the skips.

        The pass is ordered by priority then due tick.  Inside a settled window
        every due chore runs.  With no window, a ``PREEMPT`` chore may interrupt
        the running line while a ``WINDOW`` chore is skipped and postponed; a
        line that is settling just after a stop is never entered.
        """
        now = self.tick() if now is None else now
        window = window_available(state)
        actions: list[MaintAction] = []
        for sched in self.due(now):
            if window:
                actions.append(
                    MaintAction(
                        kind=sched.kind,
                        action=ACTION_RUN,
                        reason=window_label(state),
                        priority=sched.priority,
                        due_at=sched.due_at,
                    )
                )
                continue
            if state == PlantState.RUNNING and sched.interrupt == InterruptPolicy.PREEMPT:
                actions.append(
                    MaintAction(
                        kind=sched.kind,
                        action=ACTION_RUN,
                        reason="preempt",
                        priority=sched.priority,
                        due_at=sched.due_at,
                    )
                )
                continue
            reason = skip_reason(state) or "unavailable"
            post = self.postpone(sched.kind, reason, now)
            actions.append(
                MaintAction(
                    kind=sched.kind,
                    action=ACTION_SKIP,
                    reason=reason,
                    priority=sched.priority,
                    due_at=sched.due_at,
                    postponed_to=post.deferred_to,
                )
            )
        return MaintPlan(tick=now, window=window, state=str(state), actions=actions)

    # ----------------------------------------------------------- postpone / done

    def postpone(self, kind: str, reason: str, now: int | None = None) -> Postponement:
        """Defer a chore's current due cycle, idempotently.

        Repeating the call for the same due cycle returns the original record
        and does not move the deadline again.
        """
        now = self.tick() if now is None else now
        sched = self.schedule(kind)
        if sched.deferred_from is not None:
            record = self._postponements.get((kind, sched.deferred_from))
            if record is not None:
                return record
        original = sched.due_at
        deferred_to = now + sched.task_type.interval
        record = Postponement(
            kind=kind,
            deferred_from=original,
            deferred_to=deferred_to,
            reason=reason,
            tick=now,
        )
        self._postponements[record.key()] = record
        sched.due_at = deferred_to
        sched.deferred_from = original
        sched.deferred_to = deferred_to
        self._recorder.log(
            "maint/postpone",
            f"{kind} postponed from {original} to {deferred_to}: {reason}",
        )
        return record

    def complete(self, kind: str, now: int | None = None) -> None:
        """Mark a chore done at ``now`` and re-arm its interval."""
        now = self.tick() if now is None else now
        sched = self.schedule(kind)
        sched.last_done = now
        sched.due_at = now + sched.task_type.interval
        sched.deferred_from = None
        sched.deferred_to = None
        self._recorder.log("maint/complete", f"{kind} completed at {now}")

    def postponements(self) -> tuple[Postponement, ...]:
        """All recorded postponements, in idempotency-key order."""
        return tuple(self._postponements[key] for key in sorted(self._postponements))
