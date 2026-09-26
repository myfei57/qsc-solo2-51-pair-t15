"""Tick sources used to stamp control actions.

The service never reads the wall clock, so every behaviour can be reproduced
from the ordered sequence of operations alone.
"""


class LogicalClock:
    """Monotonic tick counter used in place of wall-clock time."""

    __slots__ = ("_tick",)

    def __init__(self, start: int = 0) -> None:
        if start < 0:
            raise ValueError("clock start must not be negative")
        self._tick = start

    @property
    def tick(self) -> int:
        """Current tick value."""
        return self._tick

    def advance(self, steps: int = 1) -> int:
        """Move the clock forward and return the new tick."""
        if steps < 1:
            raise ValueError("advance requires at least one step")
        self._tick += steps
        return self._tick

    def elapsed(self, since: int) -> int:
        """Number of ticks that passed since ``since``."""
        if since < 0 or since > self._tick:
            raise ValueError("elapsed reference must lie inside the tick range")
        return self._tick - since
