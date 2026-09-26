"""Alarm records raised by the monitored components."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from .ids import new_id


class Severity(IntEnum):
    """Ordered alarm severity."""

    INFO = 0
    WARNING = 1
    CRITICAL = 2

    def label(self) -> str:
        """Lower-case name used in JSON payloads."""
        return self.name.lower()

    @property
    def is_actionable(self) -> bool:
        """True for anything above informational noise."""
        return self is not Severity.INFO


@dataclass(frozen=True)
class Alarm:
    """One alarm raised by a component."""

    severity: Severity
    message: str
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly projection used by the console."""
        return {
            "id": self.id,
            "severity": self.severity.label(),
            "message": self.message,
        }


def make_alarm(severity: Severity, message: str) -> Alarm:
    """Build an alarm carrying a fresh identifier."""
    return Alarm(severity=severity, message=message, id=new_id())
