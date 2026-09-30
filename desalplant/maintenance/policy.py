"""Execution policies fixed per maintenance task type.

Whether a high-priority task may interrupt lower-priority work is never a
runtime decision: it is a property of the task type.  A task that needs the
line stopped (:data:`WindowRequirement.STOPPED`) waits for a shutdown window
even when it is the most urgent task on the ledger; only a task explicitly
marked :attr:`ExecutionPolicy.preemptive` may jump ahead of queued work.
"""

from dataclasses import dataclass
from enum import Enum


class WindowRequirement(str, Enum):
    """When a maintenance task is allowed to run."""

    RUNNING = "running"
    """Safe to perform while the line produces (e.g. a screen rinse)."""

    STOPPED = "stopped"
    """Needs a shutdown window; a running line blocks the task."""

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExecutionPolicy:
    """Fixed rule for when one task type may execute and overtake others."""

    window: WindowRequirement
    preemptive: bool = False

    @property
    def requires_stop(self) -> bool:
        """Whether the task may only start inside a shutdown window."""
        return self.window is WindowRequirement.STOPPED

    def may_preempt(self, other: "ExecutionPolicy") -> bool:
        """Whether this policy allows overtaking a task governed by ``other``."""
        return self.preemptive and not other.preemptive

    def to_dict(self) -> dict[str, object]:
        """JSON-friendly projection."""
        return {
            "window": str(self.window),
            "requires_stop": self.requires_stop,
            "preemptive": self.preemptive,
        }
