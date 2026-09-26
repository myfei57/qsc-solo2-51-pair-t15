"""Chemical tank holding the antiscalant."""

from dataclasses import dataclass


@dataclass
class ChemicalTank:
    """Tank level expressed in the same unit as the drawn amount."""

    level: float = 100.0

    def draw(self, amount: float) -> float:
        """Remove product and return the new level."""
        self.level -= float(amount)
        return self.level

    def refill(self, amount: float) -> float:
        """Add product and return the new level."""
        self.level += float(amount)
        return self.level

    def empty(self) -> bool:
        """Whether the tank ran out."""
        return self.level <= 0
