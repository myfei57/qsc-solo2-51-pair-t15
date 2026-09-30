"""Maintenance task types and their fixed operating policy.

Each recurring maintenance chore (grille cleaning, media backwash, chemical
dosing) is modelled as a :class:`TaskType` with its own interval, priority and
an ``interrupt`` policy that is fixed per task type:

* :data:`InterruptPolicy.WINDOW` -- the task may only run inside a shutdown
  window.  When the line is running or has just stopped it is skipped and
  postponed; it never interrupts production.
* :data:`InterruptPolicy.PREEMPT` -- the task is allowed to interrupt the
  running line when it is due, but it still cannot run while the line is
  settling just after a stop.

The policy is a property of the task type, not a decision an operator makes at
the console, so the ordering cannot be argued or drifted at run time.
"""

from dataclasses import dataclass
from enum import Enum


class InterruptPolicy(str, Enum):
    """Whether a task may interrupt the running line."""

    WINDOW = "window"
    PREEMPT = "preempt"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaskType:
    """A recurring maintenance chore with a fixed priority and policy."""

    kind: str
    name: str
    interval: int
    priority: int
    interrupt: InterruptPolicy

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ValueError("task interval must be positive")
        if self.priority < 1:
            raise ValueError("task priority must be positive")


# The three recurring chores the ledger unifies.  Priorities are ordered so a
# higher number wins the window; dosing is the only chore allowed to preempt.
GRILLE_CLEAN = TaskType(
    kind="grille",
    name="grille flush",
    interval=120,
    priority=2,
    interrupt=InterruptPolicy.WINDOW,
)
BACKWASH = TaskType(
    kind="backwash",
    name="media backwash",
    interval=300,
    priority=2,
    interrupt=InterruptPolicy.WINDOW,
)
DOSE = TaskType(
    kind="dose",
    name="chemical dosing",
    interval=180,
    priority=3,
    interrupt=InterruptPolicy.PREEMPT,
)

DEFAULT_TASK_TYPES: tuple[TaskType, ...] = (GRILLE_CLEAN, BACKWASH, DOSE)


@dataclass
class TaskSchedule:
    """Mutable due state for one task type.

    ``due_at`` is the tick at which the chore next becomes due.  ``deferred_from``
    is non-``None`` while the current due cycle has already been postponed once;
    it is the guard that makes a repeated postpone idempotent.
    """

    task_type: TaskType
    last_done: int = 0
    due_at: int = 0
    deferred_from: int | None = None
    deferred_to: int | None = None

    def __post_init__(self) -> None:
        if self.due_at == 0:
            self.due_at = self.task_type.interval

    @property
    def kind(self) -> str:
        return self.task_type.kind

    @property
    def priority(self) -> int:
        return self.task_type.priority

    @property
    def interrupt(self) -> InterruptPolicy:
        return self.task_type.interrupt

    def due(self, now: int) -> bool:
        """True once the clock has reached the due tick."""
        return now >= self.due_at

    def overdue(self, now: int) -> int:
        """Ticks past the due point, zero when not yet due."""
        if now < self.due_at:
            return 0
        return now - self.due_at
