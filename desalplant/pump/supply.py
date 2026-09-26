"""Supply continuity bookkeeping for the pump."""

from .state import Pump


def track_supply(pump: Pump, open_tanks: int) -> int:
    """Record how many tanks are open and stall on an empty supply."""
    return pump.track_supply(open_tanks)


def supply_continuous(previous: int, current: int) -> bool:
    """Whether the supply stayed non-empty across a step."""
    return previous > 0 and current > 0
