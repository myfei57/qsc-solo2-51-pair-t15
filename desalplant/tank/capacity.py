"""Product tank capacity projection."""

from dataclasses import dataclass
from typing import Any

from .product import ProductTank

FILL_FRACTION = 0.8


@dataclass(frozen=True)
class Capacity:
    """Total and current volume of a product tank."""

    total: float
    current: float

    def free(self) -> float:
        """Volume still available."""
        return max(self.total - self.current, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {"total": self.total, "current": self.current, "free": self.free()}


def capacity(tank: ProductTank, total: float) -> Capacity:
    """Project the tank volume from its filling and dumping state."""
    level = 0.0
    if tank.filling:
        level = total * FILL_FRACTION
    if tank.dumping:
        level = 0.0
    return Capacity(total=total, current=level)
