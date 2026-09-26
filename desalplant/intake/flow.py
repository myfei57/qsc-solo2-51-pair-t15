"""Feed ramp description used by the intake pump."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedRamp:
    """Start and end flow of a feed ramp."""

    start: float
    end: float

    def ascending(self) -> bool:
        """True when the ramp raises the flow."""
        return self.end >= self.start
