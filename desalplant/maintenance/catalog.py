"""Catalogue of the recurring maintenance tasks the ledger tracks."""

from dataclasses import dataclass
from enum import Enum

from .policy import ExecutionPolicy, WindowRequirement


class TaskType(str, Enum):
    """The maintenance families with their own intervals."""

    SCREEN_RINSE = "screen-rinse"
    """格栅冲洗: rinse the intake screen/rack."""

    MEDIA_BACKWASH = "media-backwash"
    """反洗: backwash the multi-media filter bed."""

    DOSE_CHECK = "dose-check"
    """加药: verify the antiscalant dosing run."""

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaskDef:
    """Interval, priority and fixed policy of one maintenance family."""

    type: TaskType
    label: str
    interval: int
    lead: int
    priority: int
    policy: ExecutionPolicy

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ValueError("maintenance interval must be positive")
        if self.lead < 0:
            raise ValueError("lead time must not be negative")
        if self.priority < 1:
            raise ValueError("priority must be positive")

    def first_due(self, now: int) -> int:
        """First due tick for a freshly registered task."""
        return now + self.interval

    def to_dict(self) -> dict[str, object]:
        """JSON-friendly projection."""
        return {
            "type": str(self.type),
            "label": self.label,
            "interval": self.interval,
            "lead": self.lead,
            "priority": self.priority,
            "policy": self.policy.to_dict(),
        }


# Priority 1 is the most urgent.  The policies below are deliberately fixed:
# a screen rinse can run under production and a critical rinse may overtake
# queued work, whereas the backwash and the dosing check always wait for a
# shutdown window regardless of their priority.
DEFAULT_TASKS: tuple[TaskDef, ...] = (
    TaskDef(
        type=TaskType.SCREEN_RINSE,
        label="格栅冲洗",
        interval=120,
        lead=20,
        priority=1,
        policy=ExecutionPolicy(WindowRequirement.RUNNING, preemptive=True),
    ),
    TaskDef(
        type=TaskType.MEDIA_BACKWASH,
        label="反洗",
        interval=300,
        lead=40,
        priority=2,
        policy=ExecutionPolicy(WindowRequirement.STOPPED, preemptive=False),
    ),
    TaskDef(
        type=TaskType.DOSE_CHECK,
        label="加药",
        interval=240,
        lead=30,
        priority=3,
        policy=ExecutionPolicy(WindowRequirement.STOPPED, preemptive=False),
    ),
)


class Catalog:
    """Read-only lookup of the maintenance task definitions."""

    def __init__(self, tasks: tuple[TaskDef, ...] = DEFAULT_TASKS) -> None:
        by_type: dict[str, TaskDef] = {}
        for task in tasks:
            key = str(task.type)
            if key in by_type:
                raise ValueError(f"duplicate maintenance task type {key}")
            by_type[key] = task
        self._tasks = tuple(tasks)
        self._by_type = by_type

    def __iter__(self):
        return iter(self._tasks)

    def __len__(self) -> int:
        return len(self._tasks)

    def types(self) -> tuple[TaskDef, ...]:
        """All task definitions in catalogue order."""
        return self._tasks

    def get(self, task_type: str | TaskType) -> TaskDef:
        """Look up a definition, raising on an unknown task type."""
        key = str(task_type)
        try:
            return self._by_type[key]
        except KeyError:
            raise KeyError(f"unknown maintenance task type {key}") from None

    def has(self, task_type: str | TaskType) -> bool:
        """Whether a task type is defined."""
        return str(task_type) in self._by_type
