"""Flush-gated pump stop."""

from ..flush.start import StopGate
from .state import Pump


def stop(pump: Pump, flusher) -> bool:
    """Flush the membranes before the pump is allowed to stop."""
    StopGate(pump.running).flush(flusher)
    pump.running = False
    pump.stopped = True
    return pump.stopped
