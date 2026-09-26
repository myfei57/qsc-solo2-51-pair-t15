"""Running history of backwash head losses."""

from dataclasses import dataclass, field


@dataclass
class BackwashHistory:
    """Accumulates the head loss recorded at each backwash."""

    runs: int = 0
    total_drop: float = 0.0
    drops: list[float] = field(default_factory=list)

    def record(self, drop: float) -> None:
        """Record one backwash head loss."""
        self.runs += 1
        self.total_drop += drop
        self.drops.append(float(drop))

    def average_drop(self) -> float:
        """Mean head loss across the recorded backwashes."""
        if self.runs == 0:
            return 0.0
        return self.total_drop / self.runs

    def worst_drop(self) -> float:
        """Largest head loss seen so far."""
        if not self.drops:
            return 0.0
        return max(self.drops)
