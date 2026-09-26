"""Membrane condition reported to the alarm console."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MembraneAlarm:
    """Whether a membrane is cracked and whether it is fouled."""

    cracked: bool
    fouled: bool

    def to_dict(self) -> dict[str, Any]:
        return {"cracked": self.cracked, "fouled": self.fouled}
