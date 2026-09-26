"""Product transfer between two tanks of the set."""

from dataclasses import dataclass

from ..errors import TransferFailedError
from .tanks import TankSet


@dataclass(frozen=True)
class Transfer:
    """Source, destination and volume of a transfer."""

    source: str
    destination: str
    amount: float


def transfer(tanks: TankSet, move: Transfer) -> float:
    """Validate a transfer and return its volume."""
    if move.amount <= 0:
        raise TransferFailedError("tank transfer failed")
    if move.source not in tanks.tanks:
        raise TransferFailedError("tank transfer failed")
    if move.destination not in tanks.tanks:
        raise TransferFailedError("tank transfer failed")
    return move.amount


def allowed(tanks: TankSet, move: Transfer) -> bool:
    """Whether a transfer would be accepted."""
    try:
        transfer(tanks, move)
    except TransferFailedError:
        return False
    return True
