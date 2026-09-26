"""Recovery latch handling for the brine valve."""

from ..errors import AlarmNotActiveError
from ..ro.recovery import Recovery
from .valve import Valve


class RecoveryGate:
    """Clears a recovery latch and leaves the valve emergency position."""

    def clear(self, recovery: Recovery, valve: Valve) -> None:
        """Clear the latch; it has to be active for the clear to count."""
        if not recovery.active():
            raise AlarmNotActiveError("recovery alarm not active")
        recovery.clear_alarm()
        valve.release_emergency()


def recover_alarm(valve: Valve, recovery: Recovery) -> bool:
    """Release the emergency position once the latch cleared."""
    gate = RecoveryGate()
    try:
        gate.clear(recovery, valve)
    except AlarmNotActiveError:
        valve.set_emergency()
        return False
    return True
