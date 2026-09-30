"""The ordered maintenance plan produced by one resolve pass.

Actions are sorted by priority then due tick so the console sees a stable
sequence; a skip always carries its reason and the postponement it produced.
"""

from dataclasses import dataclass, field
from typing import Any

from .postpone import Postponement

ACTION_RUN = "run"
ACTION_SKIP = "skip"


@dataclass(frozen=True)
class MaintAction:
    """One chore's decision for the current tick."""

    kind: str
    action: str
    reason: str
    priority: int
    due_at: int
    postponed_to: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly projection."""
        return {
            "kind": self.kind,
            "action": self.action,
            "reason": self.reason,
            "priority": self.priority,
            "due_at": self.due_at,
            "postponed_to": self.postponed_to,
        }


@dataclass
class MaintPlan:
    """Resolved actions for one tick, in execution order."""

    tick: int
    window: bool
    state: str
    actions: list[MaintAction] = field(default_factory=list)

    def runnable(self) -> tuple[MaintAction, ...]:
        """Chores cleared to run, in priority order."""
        return tuple(action for action in self.actions if action.action == ACTION_RUN)

    def skipped(self) -> tuple[MaintAction, ...]:
        """Chores deferred this pass, each with a reason."""
        return tuple(action for action in self.actions if action.action == ACTION_SKIP)

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly projection."""
        return {
            "tick": self.tick,
            "window": self.window,
            "state": self.state,
            "runnable": [action.to_dict() for action in self.runnable()],
            "skipped": [action.to_dict() for action in self.skipped()],
            "actions": [action.to_dict() for action in self.actions],
        }
