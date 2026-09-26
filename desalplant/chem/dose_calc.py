"""Running history of delivered dose volumes."""

from dataclasses import dataclass, field


@dataclass
class DoseHistory:
    """Accumulates the dose volume delivered by each run."""

    total: float = 0.0
    count: int = 0
    volumes: list[float] = field(default_factory=list)

    def record(self, volume: float) -> None:
        """Record one delivered volume."""
        self.total += float(volume)
        self.count += 1
        self.volumes.append(float(volume))

    def average(self) -> float:
        """Mean delivered volume."""
        if self.count == 0:
            return 0.0
        return self.total / self.count

    def largest(self) -> float:
        """Largest delivered volume so far."""
        if not self.volumes:
            return 0.0
        return max(self.volumes)
