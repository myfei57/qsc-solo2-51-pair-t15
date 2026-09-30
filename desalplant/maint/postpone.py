"""A single idempotent postponement of one maintenance chore.

A postponement is keyed by the chore and the due cycle it defers
(``deferred_from``).  Asking to postpone the same chore again for the same cycle
returns the original record instead of moving the deadline a second time, so a
duplicated or concurrent skip request cannot顺延 twice.
"""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Postponement:
    """Record of one deferred due cycle."""

    kind: str
    deferred_from: int
    deferred_to: int
    reason: str
    tick: int

    def key(self) -> tuple[str, int]:
        """Idempotency key: the chore plus the due cycle it defers."""
        return (self.kind, self.deferred_from)

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly projection for the console and audit trail."""
        return {
            "kind": self.kind,
            "deferred_from": self.deferred_from,
            "deferred_to": self.deferred_to,
            "reason": self.reason,
            "tick": self.tick,
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "Postponement":
        """Rebuild a postponement from a persisted row."""
        return cls(
            kind=str(row["kind"]),
            deferred_from=int(row["deferred_from"]),
            deferred_to=int(row["deferred_to"]),
            reason=str(row.get("reason", "")),
            tick=int(row.get("tick", 0)),
        )
