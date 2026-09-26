"""Flusher and the gate that keeps the pump running until the flush lands."""

from ..errors import FlushNotEffectiveError, PumpAlreadyStoppedError


class Flusher:
    """Runs one flush and records whether it took effect."""

    def __init__(self, available: bool = True) -> None:
        self.started = False
        self.effective = False
        self.available = available

    def start(self, pump_running: bool) -> bool:
        """Start the flush; it only takes effect with the pump running."""
        self.started = True
        self.effective = pump_running and self.available
        return self.effective


class StopGate:
    """Flush the membranes before the pump is allowed to stop."""

    def __init__(self, pump_running: bool) -> None:
        self._pump_running = pump_running

    def flush(self, flusher: Flusher) -> None:
        """Run the flush; a stopped pump makes the stop meaningless."""
        if not self._pump_running:
            raise PumpAlreadyStoppedError("pump already stopped")
        if not flusher.start(True):
            raise FlushNotEffectiveError("membrane flush not effective")
