"""Membrane flow gate that has to be satisfied before pressurising."""

from ..errors import FlowNotReadyError
from .membrane import Membrane


class FlowGate:
    """Checks that the membrane flow reached its minimum."""

    def __init__(self, minimum: float) -> None:
        self._minimum = float(minimum)

    @property
    def minimum(self) -> float:
        """Required minimum flow."""
        return self._minimum

    def satisfied(self, flow: float) -> bool:
        """Whether a flow reading reaches the minimum."""
        return flow >= self._minimum

    def confirm(self, flow: float) -> float:
        """Confirm the flow, raising when it is below the minimum."""
        if not self.satisfied(flow):
            raise FlowNotReadyError("membrane flow below minimum")
        return flow


class FlowCheck:
    """Captures the current membrane flow for telemetry."""

    def __init__(self) -> None:
        self.reading = 0.0

    def measure(self, membrane: Membrane) -> float:
        """Record and return the membrane flow."""
        self.reading = membrane.flow
        return self.reading
