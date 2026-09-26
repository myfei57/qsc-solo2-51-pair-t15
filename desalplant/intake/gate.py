"""Intake gate guarding the raw water path."""

from .interlock import GateInterlock


class Gate:
    """A single gate that is opened or closed by the intake logic."""

    def __init__(self) -> None:
        self.open = False

    def open_gate(self) -> None:
        """Open the gate."""
        self.open = True

    def close_gate(self) -> None:
        """Close the gate."""
        self.open = False

    def interlocked(self, interlock: GateInterlock, pressure: float) -> bool:
        """Open the gate only when the interlock permits it."""
        if not interlock.can_open(pressure):
            return False
        self.open_gate()
        return True
