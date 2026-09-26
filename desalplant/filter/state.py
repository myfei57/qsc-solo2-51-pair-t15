"""Inspection result for the filter rack."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RackState:
    """Growth score and blockage flag for a rack inspection."""

    growth_score: float
    blocked: bool

    def to_dict(self) -> dict[str, Any]:
        return {"growth_score": self.growth_score, "blocked": self.blocked}
