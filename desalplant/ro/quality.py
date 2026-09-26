"""Permeate grading against the conductivity limit."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PermeateGrade:
    """Grade label and safety flag for permeate."""

    grade: str
    safe: bool

    @classmethod
    def from_conductivity(cls, conductivity: float, max_cond: float) -> "PermeateGrade":
        """Grade permeate from its conductivity."""
        if conductivity <= max_cond:
            return cls(grade="acceptable", safe=True)
        return cls(grade="reject", safe=False)

    def to_dict(self) -> dict[str, Any]:
        return {"grade": self.grade, "safe": self.safe}
