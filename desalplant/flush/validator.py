"""Validation of a flush plan."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from .stage import FlushPlan


def valid(flush_plan: "FlushPlan") -> bool:
    """A plan is valid when it has stages with names and positive durations."""
    if not flush_plan.stages:
        return False
    for stage in flush_plan.stages:
        if not stage.name or stage.seconds <= 0:
            return False
    return True
