"""Flush stages and the plan built from them."""

from dataclasses import dataclass
from typing import Any, Iterable

from .validator import valid


@dataclass(frozen=True)
class Stage:
    """One named stage of a flush program."""

    name: str
    seconds: int

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "seconds": self.seconds}


@dataclass(frozen=True)
class FlushPlan:
    """An ordered list of flush stages."""

    stages: tuple[Stage, ...]

    def total_seconds(self) -> int:
        """Combined duration of every stage."""
        return sum(stage.seconds for stage in self.stages)

    def valid(self) -> bool:
        """Whether the plan is usable, i.e. every stage is well formed."""
        return valid(self)

    def names(self) -> tuple[str, ...]:
        """Stage names in program order."""
        return tuple(stage.name for stage in self.stages)


def plan(stages: Iterable[Stage]) -> FlushPlan:
    """Build a flush plan from stages."""
    return FlushPlan(stages=tuple(stages))
