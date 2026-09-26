"""Running history of tank levels."""

from dataclasses import dataclass, field


@dataclass
class LevelHistory:
    """Accumulates level samples and summarises them."""

    samples: list[float] = field(default_factory=list)

    def record(self, value: float) -> int:
        """Append a level sample and return the sample count."""
        self.samples.append(float(value))
        return len(self.samples)

    def min(self) -> float:
        """Lowest recorded level."""
        if not self.samples:
            return 0.0
        return min(self.samples)

    def max(self) -> float:
        """Highest recorded level."""
        if not self.samples:
            return 0.0
        return max(self.samples)

    def average(self) -> float:
        """Mean recorded level."""
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)

    def span(self) -> float:
        """Difference between the highest and lowest recorded level."""
        return self.max() - self.min()
