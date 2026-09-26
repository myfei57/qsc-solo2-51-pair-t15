"""Staged flush program."""

from dataclasses import dataclass, field
from typing import Iterable

from .stage import Stage


@dataclass
class Program:
    """Cursor over an ordered list of flush stages."""

    stages: tuple[Stage, ...] = field(default_factory=tuple)
    current: int = 0

    def advance(self) -> bool:
        """Move to the next stage, reporting whether one remained."""
        if self.current >= len(self.stages):
            return False
        self.current += 1
        return True

    def remaining(self) -> int:
        """Stages left to run."""
        if self.current >= len(self.stages):
            return 0
        return len(self.stages) - self.current

    def complete(self) -> bool:
        """Whether every stage has run."""
        return self.current >= len(self.stages)


def program(stages: Iterable[Stage]) -> Program:
    """Build a program from stages."""
    return Program(stages=tuple(stages))
