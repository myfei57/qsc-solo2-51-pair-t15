"""Lifecycle states of the staged line."""

from enum import Enum


class PlantState(str, Enum):
    """Coarse lifecycle of the line, in the order they may occur."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"

    def __str__(self) -> str:
        return self.value
