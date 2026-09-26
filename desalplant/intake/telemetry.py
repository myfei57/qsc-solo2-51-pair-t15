"""Intake sweep reported by the raw water pump."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntakeTelemetry:
    """Flow and screen head loss captured in one sweep."""

    flow: float
    screen_delta: float

    def fouled(self, limit: float) -> bool:
        """True when the captured head loss exceeds the cleaning limit."""
        return self.screen_delta > limit

    def to_dict(self) -> dict[str, Any]:
        return {"flow": self.flow, "screen_delta": self.screen_delta}
