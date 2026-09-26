"""Tank handoff that has to open the standby tank before closing the current."""

from ..errors import HandoffIncompleteError, SupplyInterruptedError
from ..pump.state import Pump
from ..pump.supply import supply_continuous
from .tanks import TankSet


class HandoffGate:
    """Remembers whether the standby opened and the current closed."""

    def __init__(self) -> None:
        self.opened = False
        self.closed = False

    def open_standby(self, tanks: TankSet) -> None:
        """Open the standby tank's outlet."""
        self.opened = tanks.open(tanks.standby)

    def close_current(self, tanks: TankSet) -> None:
        """Close the current tank's outlet."""
        self.closed = tanks.close(tanks.current)

    def complete(self) -> bool:
        """Whether both halves of the handoff happened."""
        return self.opened and self.closed


def handoff(tanks: TankSet, pump: Pump) -> str:
    """Move production to the standby tank without dropping the supply."""
    gate = HandoffGate()
    previous = tanks.open_count()
    gate.open_standby(tanks)
    if not gate.opened:
        raise HandoffIncompleteError("standby tank did not open")
    pump.track_supply(tanks.open_count())
    if not supply_continuous(previous, tanks.open_count()):
        raise SupplyInterruptedError("supply interrupted during tank handoff")
    gate.close_current(tanks)
    pump.track_supply(tanks.open_count())
    if not gate.complete():
        raise HandoffIncompleteError("tank handoff incomplete")
    tanks.swap()
    pump.reset_stall()
    return tanks.active_id()
