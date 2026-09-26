"""Ordered sensor readings collected during one sweep."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Reading:
    """A single named sensor reading."""

    sensor: str
    value: float

    def to_dict(self) -> dict[str, Any]:
        return {"sensor": self.sensor, "value": self.value}


@dataclass
class Telemetry:
    """A sweep's worth of readings, kept in arrival order."""

    readings: list[Reading] = field(default_factory=list)

    def add(self, sensor: str, value: float) -> Reading:
        """Append a reading and return it."""
        reading = Reading(sensor=sensor, value=float(value))
        self.readings.append(reading)
        return reading

    def total(self) -> float:
        """Sum of every reading in the sweep."""
        return sum(reading.value for reading in self.readings)

    def count(self) -> int:
        """Number of readings in the sweep."""
        return len(self.readings)

    def latest(self, sensor: str) -> float | None:
        """Most recent value for a sensor, or ``None`` when absent."""
        for reading in reversed(self.readings):
            if reading.sensor == sensor:
                return reading.value
        return None

    def sensors(self) -> tuple[str, ...]:
        """Distinct sensor names in first-seen order."""
        seen: dict[str, None] = {}
        for reading in self.readings:
            seen.setdefault(reading.sensor, None)
        return tuple(seen)

    def to_dict(self) -> dict[str, Any]:
        return {"readings": [reading.to_dict() for reading in self.readings]}
